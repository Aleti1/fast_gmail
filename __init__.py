from gmail import GmailApi
from helpers import Creds



def main():
    print("Main started")
    messages = GmailApi().get_inbox_messages()
    print(messages)


if __name__ == "__main__":
    main()
    raise SystemExit()
