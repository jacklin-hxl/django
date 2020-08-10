
import json

from django.shortcuts import render
from django.views import View
from search.models import ZhihuQuestionType,ZhihuAnswerType
from django.http import HttpResponse,HttpRequest
from elasticsearch import Elasticsearch
from datetime import datetime

client = Elasticsearch(hosts=["127.0.0.1"])

# Create your views here.
class IndexView(View):
    def get(self,request):
        return render(request,"index.html")

class SearchSuggest(View):
    def get(self,request):
        key_words = request.GET.get("s","")
        re_datas = []
        if key_words:
            s = ZhihuQuestionType.search()
            s = s.suggest("my_suggest",key_words,completion={
                "field":"suggest",
                "fuzzy":{
                    "fuzziness":1
                },
                "size":10
            })
            suggestions = s.execute_suggest()
            for match in suggestions.my_suggest[0].options:
                source = match._source
                re_datas.append(source["title"])
            
            return HttpResponse(json.dumps(re_datas),content_type="application/json")
        else:
            return HttpResponse(content="[]",content_type="application/json")

class SearchView(View):
    def get(self,request):
        key_words = request.GET.get("q","")
        if key_words:
            s_type = request.GET.get("s_type", "article")
            index_name = "jobbole"
            source = "cnblogs"
            if s_type == "job":
                index_name = "lagou"
                source = "拉勾网"
            if s_type == "question":
                index_name = "zhihu"
                source = "知乎"
            page = request.GET.get("p", "1")
            try:
                page = int(page)
            except:
                page = 1
            start_time = datetime.now()
            response = client.search(
                index="zhihu",
                body={
                    "query":{
                        "multi_match":{
                            "query":key_words,
                            "fields":["tags","title","content"]
                        }
                    },
                    "from":0,
                    "size":10,
                    "highlight":{
                        "pre_tags":['<span class="keyWord">'],
                        "post_tags":['</span>'],
                        "fields":{
                            "title":{},
                            "content":{}
                        }
                    }
                }
            )
            end_time = datetime.now()
            last_seconds = (end_time-start_time).total_seconds()
            total_nums = response["hits"]["total"]
            if (page%10) > 0:
                page_nums = int(total_nums/10) +1
            else:
                page_nums = int(total_nums/10)
            hit_list = []
            for hit in response["hits"]["hits"]:
                from collections import defaultdict
                hit_dict = defaultdict(str)
                if "highlight" not in hit:
                    hit["highlight"] = {}
                if "title" in hit["highlight"]:
                    hit_dict["title"] = "".join(hit["highlight"]["title"])
                else:
                    hit_dict["title"] = hit["_source"]["title"]
                if "content" in hit["highlight"]:
                    hit_dict["content"] = "".join(hit["highlight"]["content"])[:500]
                else:
                    hit_dict["content"] = hit["_source"]["content"][:500]
                hit_dict["url"] = hit["_source"]["url"]
                hit_dict["score"] = hit["_score"]

                hit_list.append(hit_dict)

            return render(request, "result.html", {"page":page,
                                                        "all_hits":hit_list,
                                                        "key_words":key_words,
                                                        "total_nums":total_nums,
                                                        "page_nums":page_nums,
                                                        "source":source,
                                                        "s_type":s_type,
                                                        "index_name":index_name,
                                                        "last_seconds":last_seconds,})
        else:
            return render(request,"index.html")

