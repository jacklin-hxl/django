
import json

from django.shortcuts import render
from django.views import View
from search.models import ZhihuQuestionType,ZhihuAnswerType
from django.http import HttpResponse,HttpRequest
from elasticsearch import Elasticsearch
from datetime import datetime
import redis

client = Elasticsearch(hosts=["192.168.140.150"])
redis_cli = redis.StrictRedis(host="192.168.140.150",password="admin123")


# Create your views here.
class IndexView(View):

    def get(self,request):
        hot_search = redis_cli.zrevrangebyscore("hot_search",max="+inf",min="-inf",start=0,num=5)
        hot_search = [i.decode("utf-8") for i in hot_search]

        return render(request,"index.html",{"hot_search":hot_search})

class SearchSuggest(View):

    def get(self,request):
        key_words = request.GET.get("s","")
        re_datas = []
        if key_words:
            # s = ZhihuQuestionType.search()
            # s = s.suggest("my_suggest",key_words,completion={
            #     "field":"suggest",
            #     "fuzzy":{
            #         "fuzziness":1
            #     },
            #     "size":10
            # })
            # suggestions = s.execute_suggest()
            body = {
            "size":10,
            "suggest":{
                "my_suggest":{
                "prefix":key_words,
                "completion":{
                    "field":"suggest",
                    "fuzzy":{
                    "fuzziness":1,
                    }
                }
                }
            }
            }
            result = client.search(index="zhihu",doc_type="zhihu_question",body=body)
            for match in result["suggest"]["my_suggest"][0]["options"]:
                source = match["_source"]
                re_datas.append(source["title"])
            
            return HttpResponse(json.dumps(re_datas),content_type="application/json")
        else:
            return HttpResponse(content="[]",content_type="application/json")

class SearchView(View):

    def get(self,request):
        key_words = request.GET.get("q","")
        hot_search = redis_cli.zrevrangebyscore("hot_search",max="+inf",min="-inf",start=0,num=5)
        hot_search = [i.decode("utf-8") for i in hot_search]
        if key_words:
            # 增加热搜词，通过redis存储搜索次数
            redis_cli.zincrby(name="hot_search",value=key_words,amount=1)
            # 获取前5个分数高的搜索词
            hot_search = redis_cli.zrevrangebyscore("hot_search",max="+inf",min="-inf",start=0,num=5)
            hot_search = [i.decode("utf-8") for i in hot_search]
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
                doc_type="zhihu_question",
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
            zhihu_question_count = redis_cli.get("zhihu_question_count")
            zhihu_question_count = int(redis_cli.get("zhihu_question_count")) if zhihu_question_count else 0
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
                hit_dict["create_time"] = hit["_source"]["create_time"]
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
                                                        "last_seconds":last_seconds,
                                                        "zhihu_question_count":zhihu_question_count,
                                                        "hot_search":hot_search,})
        else:
            return render(request,"index.html",{"hot_search":hot_search})

