import argparse
from pymongo import MongoClient
import json
import os
import re
from urllib.parse import quote_plus

def parse_mongo_uri(uri):
    """解析MongoDB连接URI"""
    if not uri.startswith("mongodb://"):
        uri = "mongodb://" + uri
    return uri

def parse_output_spec(spec):
    """解析db.collection格式的输出规范"""
    match = re.match(r'^([^.]+)\.([^.]+)$', spec)
    if not match:
        raise ValueError("输出规范格式错误，应为'db.collection'")
    return match.group(1), match.group(2)

def import_data(input_path, db_name, collection_name, mongo_uri):
    """导入数据到MongoDB"""
    client = MongoClient(mongo_uri)
    db = client[db_name]
    collection = db[collection_name]
    
    if os.path.isfile(input_path):
        # 导入单个文件
        with open(input_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
            if isinstance(data, list):
                result = collection.insert_many(data)
                print(f"已导入 {len(result.inserted_ids)} 条文档到 {db_name}.{collection_name}")
            else:
                result = collection.insert_one(data)
                print(f"已导入 1 条文档到 {db_name}.{collection_name}")
    elif os.path.isdir(input_path):
        # 导入目录下所有JSON文件
        total = 0
        for filename in os.listdir(input_path):
            if filename.endswith('.json'):
                file_path = os.path.join(input_path, filename)
                with open(file_path, 'r', encoding='utf-8') as file:
                    data = json.load(file)
                    if isinstance(data, list):
                        result = collection.insert_many(data)
                        count = len(result.inserted_ids)
                    else:
                        result = collection.insert_one(data)
                        count = 1
                    print(f"从 {filename} 导入 {count} 条文档")
                    total += count
        print(f"总共导入 {total} 条文档到 {db_name}.{collection_name}")
    else:
        raise FileNotFoundError(f"输入路径不存在: {input_path}")

def main():
    parser = argparse.ArgumentParser(description='将JSON数据导入MongoDB')
    parser.add_argument('-i', '--input', required=True, 
                        help='输入JSON文件或包含JSON文件的目录路径')
    parser.add_argument('-o', '--output', required=True,
                        help='目标位置，格式为db.collection')
    parser.add_argument('-u', '--uri', default='mongodb://localhost:27017',
                        help='MongoDB连接URI，默认为 mongodb://localhost:27017')
    parser.add_argument('--username', help='MongoDB用户名')
    parser.add_argument('--password', help='MongoDB密码')
    parser.add_argument('--host', help='MongoDB主机')
    parser.add_argument('--port', help='MongoDB端口')
    
    args = parser.parse_args()

    # 构建连接URI
    if args.username and args.password:
        # 如果有用户名密码，构建认证URI
        username = quote_plus(args.username)
        password = quote_plus(args.password)
        host = args.host or 'localhost'
        port = args.port or '27017'
        mongo_uri = f"mongodb://{username}:{password}@{host}:{port}/"
    else:
        # 否则使用提供的URI或默认URI
        mongo_uri = parse_mongo_uri(args.uri)

    # 解析输出规范
    try:
        db_name, collection_name = parse_output_spec(args.output)
    except ValueError as e:
        print(f"错误: {e}")
        return

    # 执行导入
    try:
        import_data(args.input, db_name, collection_name, mongo_uri)
    except Exception as e:
        print(f"导入过程中发生错误: {e}")

if __name__ == '__main__':
    main()
