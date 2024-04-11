from gmail import GmailApi


def main():
    print("Main started")
    messages = GmailApi().get_inbox_messages()
    print(messages)


if __name__ == "__main__":
    main()
    raise SystemExit()
