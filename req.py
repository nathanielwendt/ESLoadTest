from __future__ import print_function
from requests_futures.sessions import FuturesSession
from abc import ABCMeta
import requests
import json
import csv
import sys
import time
import random
import copy
import threading

class ProductLoader(object):
    CATALOG_ID = "catalog_id"
    SIZE = "size"

    def __init__(self):
        self.catalogs =  [
          { "catalog_id": 24, "size": 1700, "products": [] },
          { "catalog_id": 90, "size": 2100, "products": []},

          { "catalog_id": 105, "size": 23000, "products": []},
          { "catalog_id": 38, "size": 65000, "products": []},

          { "catalog_id": 80, "size": 130000, "products": []},
          { "catalog_id": 18, "size": 870000, "products": []},

          { "catalog_id": 572, "size": 8000000, "products": []}
        ]
        self.load_catalogs()

    def load_catalogs(self):
        for catalog in self.catalogs:
            id = catalog[ProductLoader.CATALOG_ID]
            size = catalog[ProductLoader.SIZE]
            path = "querydata/products_{0}.csv".format(id)
            catalog["products"] = FileUtils.load_from_csv_file(path, id)

    def get_from_catalogs(self, catalogs, num):
        import operator

        products = [entry for catalog in catalogs for entry in catalog["products"]]
        size_of_set = 0
        for catalog in catalogs:
            size_of_set += len(catalog["products"])

        res = []
        for _ in range(num):
            i = random.randint(0, size_of_set - 1)
            res.append(products[i])

        return res

    def get_small(self, num):
        small_catalogs = [cat for cat in self.catalogs if cat["size"] < 5000]
        return self.get_from_catalogs(small_catalogs, num)

    def get_medium(self, num):
        medium_catalogs = [cat for cat in self.catalogs if cat["size"] > 5000 and cat["size"] < 100000]
        return self.get_from_catalogs(medium_catalogs, num)

    def get_large(self, num):
        large_catalogs = [cat for cat in self.catalogs if cat["size"] > 100000 and cat["size"] < 1000000]
        return self.get_from_catalogs(large_catalogs, num)

    def get_xlarge(self, num):
        x_large_catalogs = [cat for cat in self.catalogs if cat["size"] > 1000000]
        return self.get_from_catalogs(x_large_catalogs, num)


class Product(object):
    def __init__(self, p_id, title, description, category, p_type, brand, catalog_id):
        self.p_id = self.strip_none(p_id)
        self.title = self.strip_none(title)
        self.description = self.strip_none(description)
        self.category = self.strip_none(category)
        self.type = self.strip_none(p_type)
        self.brand = self.strip_none(brand)
        self.catalog_id = str(catalog_id)

    def strip_none(self, val):
        return val if str(val) != "None" else None

    def __repr__(self):
        return ''.join((self.p_id, self.title, self.description, self.category, self.type, self.brand, self.catalog_id))

class FileUtils(object):
    @staticmethod
    def load_from_json_file(file):
        with open(file) as file_data:
            return json.load(file_data)

    @staticmethod
    def load_from_csv_file(file, catalog_id):
        with open(file, 'rb') as csv_file_data:
            csvreader = csv.reader(csv_file_data)
            next(csvreader) #skip header
            return [Product(l[0],l[1],l[2],l[3],l[4],l[5],catalog_id) for l in csvreader]


class Scheduler(object):
    def __init__(self, period_seconds):
        self.period_seconds = float(period_seconds)

    def start(self, func):
        starttime=time.time()
        while True:
            func()
            time.sleep(self.period_seconds - ((time.time() - starttime) % self.period_seconds))


class Templater(object):
    def __init__(self, template):
        self.template = template

    def populate(self, product):
        res = copy.deepcopy(self.template)
        res["query"]["bool"]["must_not"][0]["terms"]["productId"] = [product.p_id]
        res["query"]["bool"]["should"][0]["more_like_this"]["like"] = [product.title, product.description]
        res["query"]["bool"]["should"][1]["term"]["brand"]["value"] = product.brand
        res["query"]["bool"]["should"][2]["more_like_this"]["like"] = [product.category, product.type]
        return res


class RequestDataGenerator(object):
    def __init__(self, num_styles_multiplier, fixed_catalog_type = None):
        self.fixed_catalog_type = fixed_catalog_type
        self.num_styles_multiplier = num_styles_multiplier
        self.product_loader = ProductLoader()
        self.within_category_template = Templater(FileUtils.load_from_json_file("querydata/withinTemplateQuery.json"))
        self.outside_category_template = Templater(FileUtils.load_from_json_file("querydata/outsideTemplateQuery.json"))

    def get_num_requests(self):
        pass

    def next_sample(self):
        num_requests = self.get_num_requests()
        num_styles_requests = num_requests * self.num_styles_multiplier

        res = []
        products = self.get_products(num_styles_requests)
        for product in products:
            path = "/catalog_{0}/_search".format(product.catalog_id)
            res.append((path, self.within_category_template.populate(product)))
            res.append((path, self.outside_category_template.populate(product)))

        return res

    def get_products(self, num):
        rand = random.randint(0, 2)
        if (rand == 0 and not self.fixed_catalog_type) or self.fixed_catalog_type == "small":
            return self.product_loader.get_small(num)
        elif (rand == 1 and not self.fixed_catalog_type) or self.fixed_catalog_type == "medium":
            return self.product_loader.get_medium(num)
        elif (rand == 2 and not self.fixed_catalog_type) or self.fixed_catalog_type == "large":
            return self.product_loader.get_large(num)
        else:
            return self.product_loader.get_xlarge(num)


class FixedRequestDataGenerator(RequestDataGenerator):
    def __init__(self, num_styles_multiplier, fixed_request_size, fixed_catalog_type = None):
        super(FixedRequestDataGenerator, self).__init__(num_styles_multiplier, fixed_catalog_type)
        self.fixed_request_size = fixed_request_size

    def get_num_requests(self):
        return self.fixed_request_size

class RandomRequestDataGenerator(RequestDataGenerator):
    def __init__(self, num_styles_multiplier, fixed_catalog_type = None):
        super(RandomRequestDataGenerator, self).__init__(num_styles_multiplier, fixed_catalog_type)
        self.distribution = [9999, 5199, 2255, 870, 321, 126, 50, 20, 7, 2, 1]

    def get_num_requests(self):
        r = random.randint(1, 10000)
        num_requests = max([i + 1 for (i, element) in enumerate(self.distribution) if element >= r])
        return num_requests

class CachedRandomRequestDataGenerator(RequestDataGenerator):
    def __init__(self, num_styles_multiplier, fixed_catalog_type = None):
        super(CachedRandomRequestDataGenerator, self).__init__(num_styles_multiplier, fixed_catalog_type)
        self.distribution = [9999, 5199, 2255, 870, 321, 126, 50, 20, 7, 2, 1]

    def get_num_requests(self):
        r = random.randint(1, 10000)
        if r % 10 < 4: #cache with 40% hit rate, a hit corresponds with making no ES requests
            print("*cached")
            return 0
        else:
            num_requests = max([i + 1 for (i, element) in enumerate(self.distribution) if element >= r])
            print("*num requests: " + str(num_requests))
            return num_requests

class ESRequester(object):
    def __init__(self, endpoint):
        self.endpoint = endpoint

    def request(self, path, data):
        return requests.get(url = self.endpoint + path, data = json.dumps(data))

def test_sustained(catalog_type):
    endpoint = "https://vpc-semantic-similarity-loadtest-3twmawxvhaeog62xdy6pbdjnna.us-east-1.es.amazonaws.com"
    requester = ESRequester(endpoint)

    def execute_request(path, data):
        response = requester.request(path, data)
        resp_data = json.loads(response.text)
        print("{0},{1}".format(resp_data["took"], resp_data["hits"]["total"]))

    data_generator = CachedRandomRequestDataGenerator(
        num_styles_multiplier = 3
        #fixed_catalog_type = catalog_type
    )
    def make_requests_for_sample():
        sample = data_generator.next_sample()

        threads = []
        for (path, data) in sample:
            t = threading.Thread(target=execute_request, args=(path,data,))
            threads.append(t)
            t.start()

        for thread in threads:
            thread.join()

    scheduler = Scheduler(period_seconds = 1)
    scheduler.start(make_requests_for_sample)

def test_peak(num_fixed_requests, catalog_type):
    endpoint = "https://vpc-semantic-similarity-loadtest-3twmawxvhaeog62xdy6pbdjnna.us-east-1.es.amazonaws.com"
    requester = ESRequester(endpoint)

    data_generator = FixedRequestDataGenerator(
        num_styles_multiplier = 1,
        fixed_request_size = num_fixed_requests,
        fixed_catalog_type = catalog_type
    )
    def execute_request(path, data):
        response = requester.request(path, data)
        resp_data = json.loads(response.text)
        print("{0},{1}".format(resp_data["took"], resp_data["hits"]["total"]))

    sample = data_generator.next_sample()
    threads = []
    for (path, data) in sample:
        t = threading.Thread(target=execute_request, args=(path,data,))
        threads.append(t)
        t.start()

    for thread in threads:
        thread.join()

if __name__ == "__main__":
    #peak testing
    num_requests = int(sys.argv[1])
    catalog_type = sys.argv[2]
    test_peak(num_requests, catalog_type)

    #sustained testing
    #catalog_type = sys.argv[1]
    #test_sustained(catalog_type)
