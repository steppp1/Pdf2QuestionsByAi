mongoimport --uri="mongodb://localhost:27017" \
            --db=home \
            --collection=questions \
            --file=.json \
            --jsonArray



# 导入单个JSON文件到指定集合

```
python import_to_mongo.py -i data.json -o mydb.mycollection
```

# 导入目录下所有JSON文件
```
python import_to_mongo.py -i ./json_files/ -o mydb.mycollection
```


# 使用默认本地MongoDB
```
python import_to_mongo.py -i data.json -o test.data
```

# 使用自定义URI
```
python import_to_mongo.py -i data.json -o test.data -u "mongodb://example.com:27017"
```

# 使用用户名密码认证

```
python import_to_mongo.py -i data.json -o test.data --username admin --password secret --host localhost --port 27017
```





### 帮助信息

```
python import_to_mongo.py -h
```









python autoInsertMongo.py -i ./output/results/test/chunk_0001_result.json -o home.questions
