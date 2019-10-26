def upload_thought(address, user_id, thought):
    pass # TODO


def main(argv):
    if len(argv) != 4:
        print(f'USAGE: {argv[0]} <address> <user_id> <thought>')
        return 1
    try:
        # TODO
        print('done')
    except Exception as error:
        print(f'ERROR: {error}')
        return 1


if __name__ == '__main__':
    import sys
    sys.exit(main(sys.argv))
