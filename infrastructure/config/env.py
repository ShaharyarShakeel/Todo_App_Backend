
# Loads variables from the .env file in one place so other settings files can use them without repeating the same code.


from dotenv import load_dotenv


# Make repository-local environment values available before provider settings load.
load_dotenv()
