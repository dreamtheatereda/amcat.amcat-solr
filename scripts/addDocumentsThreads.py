"""Script that adds Amcat articles to Solr, using multiple threadsBased on https://issues.apache.org/jira/browse/SOLR-1544"""import solrimport datetime, timefrom amcat.model import articlefrom django.db import connectionimport threadingimport Queuequeue = Queue.Queue(10)class GMT1(datetime.tzinfo):    """very basic timezone object, needed for solrpy library.."""    def utcoffset(self,dt):        return datetime.timedelta(hours=1)    def tzname(self,dt):        return "GMT +1"    def dst(self,dt):        return datetime.timedelta(0)         class Worker(threading.Thread):  def __init__(self, queue, threadNum):    print "Starting worker thread " + threadNum    self.queue = queue    self.threadNum = threadNum    self.solr = solr.SolrConnection('http://localhost:8983/solr')    threading.Thread.__init__(self)      def run(self):    while True:      # thread blocks on get if nothing in the queue, sets taskdone immediately      # in case error with processing, don't block on join at end of script      print "Thread " + self.threadNum + " waiting for queue"      task = self.queue.get()      self.queue.task_done()      # process a shutdown task by exiting the loop, hence the thread      if (task == "SHUTDOWN"):        print "Thread " + self.threadNum + " recieved shutdown task, exiting"        self.solr.commit()        break      # post a single task (i.e. file) to solr      print "Retrieved " + str(task) + " from queue"      executePosting(self.solr, *task)            def executePosting(solr, start, end):    global processed        articlesDicts = []    print "selecting articles"    articles = article.Article.objects.all()[start:end]    print "finding sets"    cursor = connection.cursor()    cursor.execute("SELECT set_id, article_id FROM sets_articles WHERE article_id in(%s)" % ','.join(map(str, [a.id for a in articles])))    rows = cursor.fetchall()    print "sets found", len(rows)    setsDict = {}    for row in rows:        articleid = row[1]        setid = row[0]        if not articleid in setsDict:            setsDict[articleid] = []        setsDict[articleid].append(setid)    print "creating article dict"            for a in articles:        articlesDicts.append(dict(id=a.id, headline=a.headline, body=a.text, byline=a.byline, section=a.section, projectid=a.project_id,                                mediumid=a.medium_id, date=a.date.replace(tzinfo=GMT1()),                                sets=setsDict.get(a.id))                            )        processed += 1             print "adding"    solr.add_many(articlesDicts)    #solr.commit()                    starttime = time.time()        # create a connection to a solr servers = solr.SolrConnection('http://localhost:8983/solr')    count = article.Article.objects.count()print "total number of articles", countthreadcount = 4stepsize = 5000#stepsize = (count / threadcount) + 10print "stepsize", stepsizeprocessed = 0# start the worker threads which will block on the queue waiting for taskfor i in range(threadcount):    Worker(queue, str(i)).start()# put all of the data files into the queue, blocks add if the queue is full# commits if the number of tasks processed is >= the commit sizefor c in range(0, count, stepsize):    queue.put((c, c+stepsize))# wait for all the worker threads to complete current tasksprint "Waiting for all tasks to complete"queue.join()# shutdown worker threads by putting shutdown task onto the queueprint "Shutting down worker threads"for i in range(threadcount):    queue.put("SHUTDOWN")# wait for all the worker threads to complete current tasksprint "Waiting for all tasks to complete"queue.join()    # print "committing"# s.commit()print "optimizing"s.optimize()endtime = time.time()print endtime-starttimeprint "number of documents", processedprint "docs per second", processed / max(int(endtime-starttime), 1)# print "queries"# for q in connection.queries:    # print q# do a search# response = s.query('en', highlight=True, fields="body,headline,byline,text",hl_formatter='html')# for hit in response.results:    # print hit            # 500 in 15 sec = 2000 / minuut, 20 dagen...# 15mb voor 4000 docs# 60.000.000 docs: 500 uur, 220gb# < 20 sec voor 5000 docs = 15.000 per minuut# 53mb voor 10.000 docs# 285 seconds# number of documents 64993# docs per second 228# 272mb# totaal 60mil = 250gb, 73 uur# 4 threads, 5000 docs per batch# 176.708413124# number of documents 64993# docs per second 369# 187 sec when 10threads, 5000 per batch# 10threads, 1000 per batch# 193.289287806# number of documents 64993# docs per second 336#180 seconds for 4 threads, 10000 per batch# 4 threads, 20.000 articles # 173.262368202# number of documents 64993# docs per second 375# 6, 5000# 182.337801933# number of documents 64993# docs per second 357# 4, 5000 delayed commit# 175.441636086# number of documents 64993# docs per second 371# 4, 5000 with 48mb ramBufferSizeMB same# with 128mb:# 173.639503002# number of documents 64993# docs per second 375# with 64mb, 4 count/4# best# 170.899055958# number of documents 64993# docs per second 382# 2, 5000# 182.372364998# number of documents 64993# docs per second 357# 4, count/4 same with 3# 172.796238899# number of documents 64993# docs per second 377# 6 count/6# 180.77340889# number of documents 64993# docs per second 361# 2 count /2# 186.024703979# number of documents 64993# docs per second 349# todo: split add_many in parts# 314.9319911# number of documents 142527# docs per second 453# 409mb