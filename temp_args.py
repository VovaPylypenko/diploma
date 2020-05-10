import argparse

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('name', nargs='*', help="name of the user")
    #args = ap.parse_args()
    args = vars(ap.parse_args())
    print(args['name'])
    #print(args.name)
