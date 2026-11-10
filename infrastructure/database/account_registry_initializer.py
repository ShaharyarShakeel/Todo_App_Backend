"""Checks existing users in all databases and registers their account information in the Account Registry."""
from collections import defaultdict
from uuid import uuid4

from application.exceptions import AccountRegistryConflictError
from domain.entities.account_assignment import AccountAssignment
from infrastructure.database.provider_catalog import SUPPORTED_PROVIDERS, DatabaseCatalog
from domain.repositories.account_registry import AccountRegistry


class AccountRegistryInitializer:
    """Recovers interrupted signups and safely registers pre-existing accounts."""

    def __init__(self, registry: AccountRegistry, catalog: DatabaseCatalog):
        self.registry = registry
        self.catalog = catalog

    def initialize(self) -> None:
        self.registry.ensure_indexes()
        self._recover_pending()

        accounts_by_email_provider = defaultdict(list)
        accounts_by_provider_id = defaultdict(list)
        for provider in SUPPORTED_PROVIDERS:
            for user in self.catalog.user_repository_for(provider).list_users():
                normalized_email = user.email.strip().lower()
                identity = (provider, user.id)
                accounts_by_email_provider[(normalized_email, provider)].append(user.id)
                accounts_by_provider_id[user.id].append(identity)

        conflicts = [
            f"email {email!r} has multiple users in {provider}: {', '.join(sorted(set(user_ids)))}"
            for (email, provider), user_ids in accounts_by_email_provider.items()
            if len(set(user_ids)) > 1
        ]
        ambiguous_ids = {
            user_id: providers
            for user_id, providers in accounts_by_provider_id.items()
            if len(set(providers)) > 1
        }
        conflicts.extend(
            f"provider user ID {user_id!r} is shared by {self._describe(providers)}"
            for user_id, providers in ambiguous_ids.items()
        )

        registry_entries = self.registry.list_all()
        registry_by_email_provider = {
            (entry.email_normalized, entry.provider): entry for entry in registry_entries
        }
        if len(registry_by_email_provider) != len(registry_entries):
            conflicts.append("multiple registry records share an email within a provider")
        registry_ids = [entry.user_id for entry in registry_entries]
        if len(registry_ids) != len(set(registry_ids)):
            conflicts.append("multiple registry records share a global user ID")

        registry_provider_ids = defaultdict(list)
        for entry in registry_entries:
            registry_provider_ids[entry.provider_user_id].append(
                (entry.provider, entry.provider_user_id)
            )
            if entry.provider not in SUPPORTED_PROVIDERS:
                conflicts.append(
                    f"registry user {entry.user_id!r} has unsupported provider {entry.provider!r}"
                )
                continue
            stored_user = self.catalog.user_repository_for(entry.provider).get_by_id(
                entry.provider_user_id
            )
            if stored_user is None and entry.status == "active":
                conflicts.append(
                    f"active registry user {entry.user_id!r} is missing from "
                    f"{entry.provider}:{entry.provider_user_id}"
                )
            elif stored_user and stored_user.email.strip().lower() != entry.email_normalized:
                conflicts.append(
                    f"registry user {entry.user_id!r} points to a different provider email"
                )

        conflicts.extend(
            f"provider user ID {user_id!r} is assigned to multiple registry records"
            for user_id, assignments in registry_provider_ids.items()
            if len(assignments) > 1
        )

        for (email, provider), user_ids in accounts_by_email_provider.items():
            entry = registry_by_email_provider.get((email, provider))
            if entry and user_ids != [entry.provider_user_id]:
                conflicts.append(
                    f"email {email!r} in {provider} conflicts with its existing registry assignment"
                )

        if conflicts:
            raise AccountRegistryConflictError(
                "Account registry backfill found conflicts; no account assignment was chosen: "
                + "; ".join(sorted(set(conflicts)))
            )

        for (email, provider), user_ids in accounts_by_email_provider.items():
            if (email, provider) in registry_by_email_provider:
                continue
            provider_user_id = user_ids[0]
            self.registry.add_existing(
                AccountAssignment(
                    user_id=str(uuid4()),
                    email_normalized=email,
                    provider=provider,
                    provider_user_id=provider_user_id,
                )
            )

    def _recover_pending(self) -> None:
        for assignment in self.registry.list_pending():
            repository = self.catalog.user_repository_for(assignment.provider)
            user = repository.get_by_id(assignment.provider_user_id)
            if user is None:
                # This only removes metadata for an interrupted signup with no user row.
                self.registry.delete_pending(assignment.user_id)
                continue
            if user.email.strip().lower() != assignment.email_normalized:
                raise AccountRegistryConflictError(
                    "A pending registration's provider record does not match its reserved email."
                )
            self.registry.activate(assignment.user_id)

    @staticmethod
    def _describe(accounts) -> str:
        return ", ".join(f"{provider}:{user_id}" for provider, user_id in sorted(set(accounts)))
