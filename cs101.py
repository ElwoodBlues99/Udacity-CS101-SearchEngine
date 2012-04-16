import urllib
import socket
socket.setdefaulttimeout(10)
import logging
import robotparser
import urlparse
# in a true webcrawler you should not use re instead use a DOM parser
import re
# for sorting a nested list
from operator import itemgetter

def get_page(url):
	try:
		print "crawling:" + url
		f = urllib.urlopen(url)
		page = f.read()
		f.close()
		return page
	except:
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
def get_all_links(page):
	#does not handle relative links
	links = []
	while True:
		url,endpos = get_next_target(page)
		if url:
			links.append(url)
			page = page[endpos:]
		else:
			break
	return links
def add_to_index(index,keyword,url):
	if keyword in index:
		if url not in index[keyword]:
			index[keyword].append(url)
	else:
		index[keyword] = [url]
def split_string(source,splitlist):
	return ''.join([ w if w not in splitlist else ' ' for w in source]).split()
def add_page_to_index_re(index,url,content):
	i = 0
	# it is not a good idea to use regular expression to parse html
	# i did this just to give a quick and dirty result
	# to parse html pages in practice you should use a DOM parser
	regex = re.compile('(?<!script)[>](?![\s\#\'-<]).+?[<]')

	for words in regex.findall(content):
		word_list = split_string(words, """ ,"!-.()<>[]{};:?!-=`&""")
		for word in word_list:
			add_to_index(index,word,url)
			i += 1
	return i
def format_url(root,page):
	if page[0] == '/':
		return root + page
	return page
def crawl_web(seed,max_pages=10,max_depth=1):
	root = seed
	tocrawl = [seed]
	depth = [0]
	crawled = []
	index = {}
	graph = {}
	while tocrawl and len(crawled) < max_pages:
		page = tocrawl.pop()
		d = depth.pop()
		print "to crawl " + page
		if page not in crawled:
			print "page not in crawled"
			page = format_url(root,page)
			content = get_page(page)
			success = add_page_to_index_re(index,page,content)
			outlinks = get_all_links(content)
			graph[page] = outlinks
			if d != max_depth:
				cnt = union(tocrawl,outlinks)
				for i in range(cnt):
					depth.append(d+1)
			crawled.append(page)
			print crawled
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
			return "    Welcome to the CS101 Web Crawler\n" + \
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
				ret += "        Failed to save {0} to {0}\n".format(data_str,path)
			try:
				size = os.path.getsize(path)
			except:
				size = 0
				fail += 1
				ret += "        Failed to get the size of {0}\n".format(path)

			if fail == 0:
				ret += "        {0} was saved to {0} ({} bytes)\n".format(data_str,path,size)
				ret += "        {0} contains {0} entries.\n".format(data_str,len(data))
			file.close()
		else:
			ret += "        Failed to open {0} at {0}\n".format(data_str,path)
		print ret
	def load_file(data,data_str,path):
		ret = ""
		if os.path.exists(path):
			file1 = open(path,'rb')
			if file1:
				try:
					data = pickle.load(file1)
					size1 = os.path.getsize(path)
					ret += "        Loaded {0} from {0} ({} bytes)\n".format(data_str,path,size1)
					ret += "        {0} contains {0} entries.\n".format(data_str,len(data))
				except:
					size1 = 0
					ret += "        Failed to load {0} from {0}\n".format(data_str,path)
			else:
				ret += "        Failed to open {0}\n".format(path)
		else:
			ret += "        {0} does not exist\n".format(path)
		print ret
		return data
	def execute_cmd(c,index,graph, ranks, searches):
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
			w = raw_input("    Enter a word to find from the index:")
			ret = ""
			if len(ranks) == 0:
				ranks = compute_ranks(graph)
			l = lookup_best(index, w, ranks)
			if len(l) == 0:
				ret = "        {0} was not found in index".format(w)
			else:
				ret += "        '{0}' appears in the following urls:\n".format(w)
				for e in l:
					ret += "            {0}\n            score = {0}\n".format(e[1],e[0])
				searches.append(w)
				is_trending = {}
				if len(searches) == GLOBAL_NUM_SEARCHES:
					searches.reverse()
					is_trending = trending(searches,GLOBAL_TRENDING_INTERVAL)
					searches = []
				if len(is_trending) > 0:
					ret += "        The following are trending:\n"
					for word in is_trending:
						ret += "            '{}'\n".format(word)
				print ret
				raw_input("    Press Enter")
				print ""
		return index, graph, ranks, searches
	def main():
		index = {}
		graph = {}
		ranks = {}
		searches = []
		while(True):
			c = raw_input(print_cmds())
			if c == 'q' or c == 'Q':
				break
			index, graph, ranks, searches = execute_cmd(c,index, graph, ranks, searches)
	main()
