#Based on core code provided in the Udacity forums by Jksdrum.
#The changes/enhancements follow:
#
#Respects robots.txt to try and be a good net citizen, even though there is no offical robots.txt standard
#
#Useragent specified so crawler can be banned by Website admins if it is too agressive, and so they
#can get stats to see who is on their site and if it is a bot or not. 
#
#Provides logging of crawl for analytics and eyecandy (googleearth display)
#
#Converts strings to ascii to avoid utf8 encoding issues (especially code posted from MS word was 
#encounted, it would crash the index as multiwords links by 'invisible' characters would be stored)
#
#Converts strings to lowercase before adding them to the index, making searching non case sensitive
#
#Real world (web) problems. Not all sites have nice (valid) html. Very few do, and it would crash 
#the vanilla version from class.
#To overcome issues with tags being malformed on real web pages, and many vailid a href tags being 
#ignored, it utalises a modified crawl_web function using BeautifySoup to extract html entites, 
#originally written by David Harris (Released under a Creative Commons License)
#
#Stopwords. There are many words in english that are just common joining words, such as "why",
#"how", "our", etc, that add little value (IMHO) to the index for most searches. Who searches 
#for "on" "the", etc? So I removed them.
#I also remove any sinlge letter words ("I", "a"), as I found these being generated from many alphabetical 
#index sites, and they added nothing valuable to the returned results.
#
#Stemming is a way to derive grammatical (prefix) stems from English words. It removes possesives, 
#prefixes, suffixes, to try and get to the 'stem' of the word. My idea is to add a little fuzziness 
#to the search. For example, searching for the word "complicated" would return matches for "complicated",
#"complications", "complicating" or "complicates" 
#I also weed out and discard single character results
#I started writing my own implimentation of Porters stemming function, then discovered 
#that one came bundled with nltk. Why reinvent the wheel?
#
#Limit the domains crawled. To stop the crawl taking on the entire internet, you can limit the 
#crawl to certain domains or paths as specified in whitelist.txt. This is useful if you want to limit
#the crawl to part of a website, or to a company domain or three. This is fairly basic at the moment
#and should be extened to allow regexes and wildcards to be used.
#
#thanks goes to Addle on IRC who helped with the dictionary structures in nee_add_to_index when
#I had writers block (my brain was stuck in an infinite loop)
#

#to do
#Named entity extraction
#split crawl and search into 2 seperate programs so they car run independntly
#store last crawled page so crawls can be re-run for current position
#cgi interface

import urlparse
import nltk
from nltk import PorterStemmer
import urllib
import urllib2
import socket
socket.setdefaulttimeout(10)
import logging
import robotparser
import urlparse
from bs4 import BeautifulSoup
import html5lib
# in a true webcrawler you should not use re instead use a DOM parser
import re
# for sorting a nested list
from operator import itemgetter

def get_page(url):
	try:
		#change the useragent so sites can track/ban crawler if required
		#override default functionality, create a subclass of URLopener
		# then assign an instance of that class to the urllib._urlopener
		AGENTNAME="Udacity CS101 crawler"
		class AppURLopener(urllib.FancyURLopener):
			version = AGENTNAME
		urllib._urlopener = AppURLopener()
		logger.info('crawling: ' + url)

		print "crawling:" + url
		f = urllib.urlopen(url)
		page = f.read()
		f.close()
		return page
	except:
		logger.warn('exception raised on :' + url) #so we can debug why a page failed to crawl
		return ""
	return ""
def get_next_target(page):
	start_link = page.find('<a href=')
	if start_link == -1:
		return None, 0
	start_quote = page.find('"', start_link)
	end_quote = page.find('"', start_quote + 1)
	url = page[start_quote + 1:end_quote]
	return url, end_quote
def union(p,q):
	cnt = 0
	for e in q:
		if e not in p:
			p.append(e)
			cnt += 1
	return cnt
#def get_all_links(page):
#original does not handle relative links
#	links = []
#	while True:
#		url,endpos = get_next_target(page)
#		if url:
#			links.append(url)
#			page = page[endpos:]
#		else:
#			break
#	return links
def get_all_links(soup, page):
	links = []
	last = page.find('/', 8)
	if last > 0:
		page = page[:last]
	for link in soup.find_all('a'):
		if link.get('href'):
			if link.get('href')[0] == '/':
				links.append(page + link.get('href'))
			else:
				links.append(link.get('href'))
	return links

def add_to_index(index,keyword,url):
	if keyword in index:
		if url not in index[keyword]:
			index[keyword].append(url)
	else:
		index[keyword] = [url]


def split_string(source,splitlist):
	return ''.join([ w if w not in splitlist else ' ' for w in source]).split()
	end_split = []
	if source == "":
		return end_split
	marker = 0
	for pos in range(0, len(source) - 1):
		for j in range(0, len(splitlist)-1):
			if source[pos] == splitlist[j]:
				if len(source[marker:pos]) > 0:
					end_split.append(source[marker:pos])
					marker = pos + 1
					break
				else:
					marker = pos + 1
	pos = len(source)-1
	flag = False
	for j in range(0, len(splitlist)):
		if source[pos] == splitlist[j]:
			if len(source[marker:pos]) > 0:
				end_split.append(source[marker:pos])
				flag = True
	if not flag and len(source[marker:pos]) > 0:
		end_split.append(source[marker:])
	return end_split

def InWhiteList(page):
	#whitelist.txt restricts the domains that can be crawled
	#this allows you to limit it to specific domains so it can stay within your
	#site/orgainisation.
	#it is rather basic, and errs on the side of being greedy.
	#http:// is not required, just the hostname or directory names will do
	#each on their own line
	#if the whitelist exists, action it, otherwise return true for all domains
	#so make sure the whitelist does not disappear....	
        try:
                print page
                file=open('whitelist.txt','r')
                whitelist=file.readlines()
                file.close
                for line in whitelist:
                        print line
                        if line.rstrip('\n') in page:
                                return True
                return False
        except:
                return True



def stemming(word):
	result = word.lower()
	result=result.encode('ascii', 'ignore')
	result=PorterStemmer().stem_word(result)
	return result

def IsNotStopWord(word):
	#weeds out stops words and single character letters
        stop_words = 'i', 'me', 'my', 'myself', 'we', 'our', 'ours', 'ourselves', 'you', 'your', 'yours', 'yourself', 'yourselves', 'he', 'him', 'his', 'himself', 'she', 'her', 'hers', 'herself', 'it', 'its', 'itself', 'they', 'them', 'their', 'theirs', 'themselves', 'what', 'which', 'who', 'whom', 'this', 'that', 'these', 'those', 'am', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'having', 'do', 'does', 'did', 'doing', 'a', 'an', 'the', 'and', 'but', 'if', 'or', 'because', 'as', 'until', 'while', 'of', 'at', 'by', 'for', 'with', 'about', 'against', 'between', 'into', 'through', 'during', 'before', 'after', 'above', 'below', 'to', 'from', 'up', 'down', 'in', 'out', 'on', 'off', 'over', 'under', 'again', 'further', 'then', 'once', 'here', 'there', 'when', 'where', 'why', 'how', 'all', 'any', 'both', 'each', 'few', 'more', 'most', 'other', 'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very', 's', 't', 'can', 'will', 'just', 'don', 'should', 'now'
        if word not in stop_words and len(word)>1:
                return True
        else:
                return False

def nee_add_to_index(neeindex, neestring, url):
        if url in neeindex:
                entry = neeindex[url]
                print entry
                entry.append(neestring)
        else:
                neeindex[url] = [neestring]

def named_entity_extraction(neeindex,url,text):
#	for sent in nltk.sent_tokenize(text):
#		for chunk in nltk.ne_chunk(nltk.pos_tag(nltk.word_tokenize(sent))):
#			if hasattr(chunk, 'node'):
#				print chunk.node, ' '.join(c[0] for c in chunk.leaves())

	print "in named entity extraction"
	print "neeindex:"
	print neeindex
	print "url="+url
	print "==="
	list=[]
	a = nltk.word_tokenize(text)
	b = nltk.pos_tag(a)
	c = nltk.ne_chunk(b,binary=True)
	for x in c.subtrees():
		if x.node == "NE":
			words = [w[0] for w in x.leaves()]
			name = " ".join(words)
			print "name=" + name
			nee_add_to_index(neeindex,name,url)		
	return neeindex



def of_interest(alist):

	l=list((a, alist.count(a)) for a in set(alist))
	get_score = itemgetter(1)
	map(get_score,l)
	l = sorted(l,key=get_score)
	l.reverse()
	n=len(l)
	print n
	if n>5:
        	n=5 #limit the number of suggestions to 5
	newlist=[]
	for i in xrange(n):
		print l[i][0]
		newlist.append(l[i][0])
	print newlist
	print ", ".join(newlist)
	return (", ".join(newlist))



def add_page_to_index_re(index,url,content):
	i = 0
	# it is not a good idea to use regular expression to parse html
	# i did this just to give a quick and dirty result
	# to parse html pages in practice you should use a DOM parser
#	regex = re.compile('(?<!script)[>](?![\s\#\'-<]).+?[<]')
#	for words in regex.findall(content):
#		word_list = split_string(words, """ ,"!-.()<>[]{};:?!-=`&""")
#		for word in word_list:
#			add_to_index(index,word,url)
#			i += 1
#	return i
	words = split_string(content, "!@#$%^&*(),./?><[]}\"{':;=-~`|\\ \n")
	counter = 0
	for word in words:
		counter +=1
		if IsNotStopWord(word):
			add_to_index(index, stemming(word), url)
	return counter




def format_url(root,page):
	if page[0] == '/':
		return root + page
	return page


def roboize(page):
	start_page = page.find('/') + 2
	if page.find('/', start_page) == -1:
		return page + '/robots.txt'
	else:
		return page[:page.find('/', start_page)] + '/robots.txt'



def crawl_web(seed,max_pages=10,max_depth=1):
#	root = seed
#	tocrawl = [seed]
#	depth = [0]
#	crawled = []
#	index = {}
#	graph = {}
#	while tocrawl and len(crawled) < max_pages:
#		page = tocrawl.pop()
#		d = depth.pop()
#		print "to crawl " + page
#		if page not in crawled:
#			print "page not in crawled"
#			page = format_url(root,page)
#			#content = get_page(page)
#			try:
#				soup=BeautifulSoup(get_page(page), "html5lib")
#				soup.prettify()
#			except:
#				soup=''
#			if soup:
#				print "valid soup"
#				content=soup.get_text()
#				success = add_page_to_index_re(index,page,content)
#				#outlinks = get_all_links(content)
#				outlinks = get_all_links(soup, page)
#			else:
#				print "no soup for you"
#				outlinks=[]
#			print outlinks
#			for link in outlinks:
#				depth.append(d+1)
#			graph[page] = outlinks
#			if d != max_depth:
#				cnt = union(tocrawl,outlinks)
#				for i in range(cnt):
#					depth.append(d+1)
#			crawled.append(page)
#			print crawled #debug
#	return index, graph

	tocrawl = [seed]
	crawled = {}
	graph = {}
	index = {}
	neeindex = {}
	cache = {}
	depth = [0]
	num_pages = 0
	entities ={}
	while tocrawl and num_pages < max_pages:
		page = tocrawl.pop(0)
		page = page.lower()
		print "trying: " + page #debug
		if page[len(page)-1] == '/':
			page = page[:len(page)-1]
		not_twitter = True
		if (page.find('twitter.com') > 0 or page.find('199.59.148.11') > 0):
			if len(page) > 28:
				not_twitter = False
			else:
				not_twitter = True
                
		current_depth = depth.pop(0)
		robot = robotparser.RobotFileParser()
		print "robots.txt" #debug
		robot.set_url(roboize(page))
		try:
			robot.read()
			allowed = robot.can_fetch("*", page)
		except:
			allowed = False
			logger.info("blocked by " + roboize(page)+ " :" + page)
		if InWhiteList(urlparse.urlparse(page).hostname):
			whitelistallowed = True
		else:
			whitelistallowed = False
			print "whitelist not allowed"
		if page not in crawled and current_depth <= max_depth and num_pages < max_pages and allowed and whitelistallowed and not_twitter:
			num_pages += 1
			try:
				soup = BeautifulSoup(get_page(page), "html5lib")
				soup.prettify()
			except:
				soup = ''
			if soup:
				#extract all text from the page, removing markup
				content = soup.get_text()
				cache[page] = content #used for keywords in context
				outlinks = get_all_links(soup, page)
				add_page_to_index_re(index, page, content)
				named_entity_extraction(neeindex,page,content)
				print neeindex
			else:
				outlinks = []
			for link in outlinks:
				print "added to crawl " + link
				depth.append(current_depth + 1)
			graph[page] = outlinks
			union(tocrawl, outlinks)
			crawled[page] = True
#	return index, graph, cache
	return index, graph



def lookup(index, keyword):
	if keyword in index:
		return index[keyword]
	return None
def sort_by_score(l):
	get_score = itemgetter(0)
	map(get_score,l)
	l = sorted(l,key=get_score)
	l.reverse()
	return l
def lookup_best(index, keyword, ranks):
	result = []
	if keyword in index:
		for url in index[keyword]:
			if url in ranks:
				result.append([ranks[url], url])
	if len(result) > 0:
		result = sort_by_score(result)
	return result
def get_inlinks(page,graph):
	il = {}
	for p in graph:
		for ol in graph[p]:
			if ol == page:
				il[p] = graph[p]
	return il
def compute_ranks(graph):
	d = 0.8 # damping factor
	numloops = 10
	ranks = {}
	npages = len(graph)
	for page in graph:
		ranks[page] = 1.0 / npages
	for i in range(0, numloops):
		newranks = {}
		for page in graph:
			newrank = (1 - d) / npages
			inlinks = get_inlinks(page,graph)
			for il in inlinks:
				newrank += ((0.8 * ranks[il])/len(inlinks[il]))
			newranks[page] = newrank
		ranks = newranks
	return ranks
# code below only runs when this file is run as a script
# if you imported this code into your own module the code
# below would not be accessible by your code
if __name__ == "__main__":
	import os
	import pickle
	GLOBAL_NUM_SEARCHES = 8
	GLOBAL_TRENDING_INTERVAL = 4

	#setting up logger
	logger = logging.getLogger('webcrawler')
	hdlr = logging.FileHandler('webcrawler.log')
	formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
	hdlr.setFormatter(formatter)
	logger.addHandler(hdlr)
	logger.setLevel(logging.INFO)


	def calculate_trending(trending,now,before,interval,threshhold=0.5):
		for s in now:
			if s in before:
				slope = float(now[s] - before[s])/interval
				# set trending
				if slope > threshhold:
					trending[s] = 1
				# clear trending
				if slope < 0:
					if s in trending:
						trending.pop(s)
		return trending
	def trending(searches,interval):
		curr_searches = {}
		prev_searches = {}
		is_trending = {}
		i = 0
		while(searches):
			search = searches.pop()
			if search in curr_searches:
				curr_searches[search] = curr_searches[search] + 1
			else:
				curr_searches[search] = 1
			i += 1
			if i == interval:
				is_trending = calculate_trending(is_trending,curr_searches,prev_searches,interval)
				i = 0
				prev_searches = curr_searches.copy()
				curr_searches.clear()
		return is_trending
	def print_cmds():
			return "    Welcome to the CS101 Web Crawler version 0.2\n" + \
					"    What do you want to do?\n" + \
					"    Enter 1 - To start crawling a web page\n" + \
					"    Enter 2 - Print the Index\n" + \
					"    Enter 3 - Find a word in the Index\n" + \
					"    Enter 4 - Save Index\n" + \
					"    Enter 5 - Load Index\n" + \
					"    Enter 6 - Delete Index\n" + \
					"    Enter q - Quit\n" + \
					"    crawler:"
	def execute_start_crawl(index):
		maxdepth = int(raw_input("    Enter Max Depth:"))
		maxpages = int(raw_input("    Enter Max Pages:"))
		url = raw_input("    Enter Web Url:")
		return crawl_web(url,maxpages,maxdepth)
	def delete_file(path):
		ret = ""
		if os.path.exists(path):
			try:
				size2 = os.path.getsize(path)
				os.remove(path)
				ret += "        Deleted {} ({} bytes)\n".format(path,size2)
			except:
				ret += "        Failed to delete {}\n".format(path)
			print ret
	def clear_data(data,data_str,path):
		ret = ''
		delete_file(path)
		length = len(data)
		data.clear()
		ret += "        Cleared {} entries from {}\n".format(length,data_str)
		print ret
		return data
	def open_file(data,data_str,path):
		ret = ""
		file = open(path,"wb")
		if file:
			fail = 0
			try:
				pickle.dump(data,file)
			except:
				fail += 1
				ret += "        Failed to save {0} to {1}\n".format(data_str,path)
			try:
				size = os.path.getsize(path)
			except:
				size = 0
				fail += 1
				ret += "        Failed to get the size of {0}\n".format(path)

			if fail == 0:
				ret += "        {0} was saved to {1} ({2} bytes)\n".format(data_str,path,size)
				ret += "        {0} contains {1} entries.\n".format(data_str,len(data))
			file.close()
		else:
			ret += "        Failed to open {0} at {1}\n".format(data_str,path)
		print ret
	def load_file(data,data_str,path):
		ret = ""
		if os.path.exists(path):
			file1 = open(path,'rb')
			if file1:
				try:
					data = pickle.load(file1)
					size1 = os.path.getsize(path)
					ret += "        Loaded {0} from {1} ({2} bytes)\n".format(data_str,path,size1)
					ret += "        {0} contains {1} entries.\n".format(data_str,len(data))
				except:
					size1 = 0
					ret += "        Failed to load {0} from {1}\n".format(data_str,path)
			else:
				ret += "        Failed to open {0}\n".format(path)
		else:
			ret += "        {0} does not exist\n".format(path)
		print ret
		return data
	def execute_cmd(c, neeindex, index, graph, ranks, searches):
		if c == '1':
			index, graph = execute_start_crawl(index)
			ranks = compute_ranks(graph)
			print "    Crawl finished.  Index has {0} items.".format(len(index))
			raw_input("    Press Enter")
			print ""
		elif c == '2':
			maxentries = raw_input("    Enter Number of Index Entries to Display (Type a for all):")
			if maxentries == 'a' or maxentries == 'A':
				maxentries = 0xFFFFFFFF
			else:
				maxentries = int(maxentries)
			for i, e in enumerate(index):
				if i >= maxentries:
					break
				print "        Entry {0}:".format(i)
				print "            '{0}' appears in the following urls:".format(e)
				for u in index[e]:
					print "                {0}".format(u)
			if len(index) == 0:
				print "        Index is empty"
			raw_input("    Press Enter")
			print ""
		elif c == '4':
			open_file(index,"Index",os.getcwd() + os.path.sep + 'index.pkl')
			open_file(graph,"Graph",os.getcwd() + os.path.sep + 'graph.pkl')
			open_file(ranks,"Ranks",os.getcwd() + os.path.sep + 'ranks.pkl')
			raw_input("    Press Enter")
			print ""
		elif c == '5':
			index = load_file(index,"Index",os.getcwd() + os.path.sep + 'index.pkl')
			graph = load_file(graph,"Graph",os.getcwd() + os.path.sep + 'graph.pkl')
			ranks = load_file(ranks,"Ranks",os.getcwd() + os.path.sep + 'ranks.pkl')
			raw_input("    Press Enter")
			print ""
		elif c == '6':
			index = clear_data(index,"Index",os.getcwd() + os.path.sep + 'index.pkl')
			graph = clear_data(graph,"Graph",os.getcwd() + os.path.sep + 'graph.pkl')
			ranks = clear_data(ranks,"Ranks",os.getcwd() + os.path.sep + 'ranks.pkl')
			searches = []
			raw_input("    Press Enter")
			print ""
		else:
			topindex=[]
			w = raw_input("    Enter a word to find from the index:")
			ret = ""
			realword=w
			w=PorterStemmer().stem_word(w)
			if len(ranks) == 0:
				ranks = compute_ranks(graph)
			l = lookup_best(index, w, ranks)
			if len(l) == 0:
				ret = "        {0} was not found in index".format(realword)
			else:
				ret += "        '{0}' appears in the following urls:\n".format(realword)
				for e in l:
					print e	
					topindex.append(neeindex[e])
					
				print of_interest(topindex)		
				for e in l:
					ret += "            {0}\n            score = {1}\n".format(e[1],e[0])
										
				searches.append(w)
				is_trending = {}
				if len(searches) == GLOBAL_NUM_SEARCHES:
					searches.reverse()
					is_trending = trending(searches,GLOBAL_TRENDING_INTERVAL)
					searches = []
				if len(is_trending) > 0:
					ret += "        The following are trending:\n"
					for word in is_trending:
						ret += "            '{0}'\n".format(word)
				print ret
				raw_input("    Press Enter")
				print ""
		return neeindex, index, graph, ranks, searches
	def main():
		index = {}
		neeindex = {}
		graph = {}
		ranks = {}
		searches = []
		while(True):
			c = raw_input(print_cmds())
			if c == 'q' or c == 'Q':
				break
			neeindex, index, graph, ranks, searches = execute_cmd(c, neeindex, index, graph, ranks, searches)
	main()
