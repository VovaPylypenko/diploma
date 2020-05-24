import pymongo
import datetime


if __name__ == '__main__':
    client = pymongo.MongoClient(
        "mongodb+srv://admin:admin@cluster0-d70d1.mongodb.net/test?retryWrites=true&w=majority")
    db = client['test']
    col = db['test-col2']

    new_posts = [
        {
            "author": "Mike",
            "text": "Another post!",
            "tags": {
                'test1': 'test2',
                'test2': 'test1'
            },
            "date": datetime.datetime(2009, 11, 12, 11, 14)
        },
        {
            "author": "Eliot",
            "title": "MongoDB is fun",
            "text": "and pretty easy too!",
            "date": datetime.datetime(2009, 11, 10, 10, 45)
        }
    ]

    #result = col.find_one({'author': 'Eliot'})
    f = None
    result = col.insert_many(new_posts)

    print(result)
