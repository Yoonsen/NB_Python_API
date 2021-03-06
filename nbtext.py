import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from collections import Counter
import json
import requests
from IPython.display import HTML
import seaborn as sns
from scipy.spatial.distance import cosine
import networkx as nx
try:
    from wordcloud import WordCloud
except:
    "Wordcloud -- hmmm"

def totals(top=200):
    import requests
    r = requests.get("https://api.nb.no/ngram/totals", json={'top':top})
    return dict(r.json())

def navn(urn):
    import requests
    if type(urn) is list:
        urn = urn[0]
    r = requests.get('https://api.nb.no/ngram/tingnavn', json={'urn':urn})
    return dict(r.json())
    
def urn_from_text(T):
    """Return URNs as 13 digits (any sequence of 13 digits is counted as an URN)"""
    import re
    return re.findall("(?<=digibok_)[0-9]{13}", T)

def metadata(urn="""text"""):
    import requests
    if type(urn) is str:
        urns = urn
    elif type(urn) is list:
        urns = '-'.join([str(u) for u in urn])
    else:
        urns = str(urn)
        
    r = requests.get("https://api.nb.no/ngram/meta", params={'urn':urns})
    return r.json()

def pure_urn(data):
    """Convert URN-lists with extra data into list of serial numbers"""
    if type(data) is list and type(data[0]) is list:
        try:
            res = [x[0] for x in data]
        except:
            res = []
    elif type(data) is list and not type(data[0]) is list:
        res = data
    elif type(data) is str:
        res = urn_from_text(data)
    else:
        res = []
    return res


def difference(first, second, rf, rs, years=(1980, 2000),smooth=1, corpus='bok'):
    """Compute difference of difference (first/second)/(rf/rs)"""
    try:
        a_first = nb_ngram(first, years=years, smooth=smooth, corpus=corpus)
        a_second = nb_ngram(second, years=years, smooth=smooth, corpus=corpus)
        a = a_first.join(a_second)  
        b_first = nb_ngram(rf, years=years, smooth=smooth, corpus=corpus)
        b_second = nb_ngram(rs, years=years, smooth=smooth, corpus=corpus)
        if rf == rs:
            b_second.columns = [rs + '2']
        b = b_first.join(b_second)
        s_a = a.mean()
        s_b = b.mean()
        f1 = s_a[a.columns[0]]/s_a[a.columns[1]]
        f2 = s_b[b.columns[0]]/s_b[b.columns[1]]
        res = f1/f2
    except:
        res = 'Mangler noen data - har bare for: ' + ', '.join([x for x in a.columns.append(b.columns)])
    return res
    

def col_agg(df, col='sum'):
    c = df.sum(axis=0)
    c = pd.DataFrame(c)
    c.columns = [col]
    return c

def row_agg(df, col='sum'):
    c = df.sum(axis=1)
    c = pd.DataFrame(c)
    c.columns = [col]
    return c


def get_freq(urn, top=50, cutoff=3):
    """Get frequency list for urn"""
    r = requests.get("https://api.nb.no/ngram/urnfreq", json={'urn':urn, 'top':top, 'cutoff':cutoff})
    return Counter(dict(r.json()))


def get_urn(metadata=None):
    """Get urns from metadata"""
    if metadata is None:
        metadata = {}
    if not ('next' in metadata or 'neste' in metadata):
        metadata['next'] = 100
    if not 'year' in metadata:
        metadata['year'] = 1900
    r = requests.get('https://api.nb.no/ngram/urn', json=metadata)
    return r.json()

def get_papers(top=5, cutoff=5, navn='%', yearfrom=1800, yearto=2020, samplesize=100):
    """Get newspapers"""
    div = lambda x, y: (int(x/y), x % y)
    chunks = 20
    
    
    # split samplesize into chunks, go through the chunks and then the remainder
    
    (first, second) = div(samplesize, chunks)
    r = []
    
    # collect chunkwise 
    for i in range(first):
        r += requests.get("https://api.nb.no/ngram/avisfreq", json={'navn':navn, 'top':top, 'cutoff':cutoff,
                                                              'yearfrom':yearfrom, 'yearto':yearto,'samplesize':chunks}
                         ).json()
    
    
    # collect the remainder
    r += requests.get("https://api.nb.no/ngram/avisfreq", json={'navn':navn, 'top':top, 'cutoff':cutoff,
                                                              'yearfrom':yearfrom, 'yearto':yearto,'samplesize':second}
                         ).json()

    return [dict(x) for x in r]

def collocation(word, yearfrom=2010, yearto=2018, before=3, after=3, limit=1000, corpus='avis'):
    data =  requests.get(
        "https://api.nb.no/ngram/collocation", 
        params={
            'word':word,
            'corpus':corpus, 
            'yearfrom':yearfrom, 
            'before':before,
            'after':after,
            'limit':limit,
            'yearto':yearto}).json()
    return pd.DataFrame.from_dict(data['freq'], orient='index')

def heatmap(df, color='green'):
    return df.fillna(0).style.background_gradient(cmap=sns.light_palette(color, as_cmap=True))

def get_corpus_text(urns, top = 10000, cutoff=5):
    k = dict()
    for u in urns:
        #print(u)
        k[u] = get_freq(u, top = top, cutoff = cutoff)
    return pd.DataFrame(k)

def normalize_corpus_dataframe(df):
    colsums = df.sum()
    for x in colsums.index:
        #print(x)
        df[x] = df[x].fillna(0)/colsums[x]
    return True

def show_korpus(korpus, start=0, size=4, vstart=0, vsize=20, sortby = ''):
    """Show corpus as a panda dataframe
    start = 0 indicates which dokument to show first, dataframe is sorted according to this
    size = 4 how many documents (or columns) are shown
    top = 20 how many words (or rows) are shown"""
    if sortby != '':
        val = sortby
    else:
        val = korpus.columns[start]
    return korpus[korpus.columns[start:start+size]].sort_values(by=val, ascending=False)[vstart:vstart + vsize]

def aggregate(korpus):
    """Make an aggregated sum of all documents across the corpus, here we use average"""
    return pd.DataFrame(korpus.fillna(0).mean(axis=1))

def convert_list_of_freqs_to_dataframe(referanse):
    """The function get_papers() returns a list of frequencies - convert it"""
    res = []
    for x in referanse:
        res.append( dict(x))
    result = pd.DataFrame(res).transpose()
    normalize_corpus_dataframe(result)
    return result

def get_corpus(top=5, cutoff=5, navn='%', corpus='avis', yearfrom=1800, yearto=2020, samplesize=10):
    if corpus == 'avis':
        result = get_papers(top=top, cutoff=cutoff, navn=navn, yearfrom=yearfrom, yearto=yearto, samplesize=samplesize)
        res = convert_list_of_freqs_to_dataframe(result)
    else:
        urns = get_urn({'author':navn, 'year':yearfrom, 'neste':yearto-yearfrom, 'limit':samplesize})
        res = get_corpus_text([x[0] for x in urns], top=top, cutoff=cutoff)
    return res


class Cluster:
    from IPython.display import HTML, display
    import pandas as pd
    import json
    
    def __init__(self, word = '', filename = '', period = (1950,1960) , before = 5, after = 5, corpus='avis', reference = 200, 
                 word_samples=1000):
        import pandas
        
        if word != '':
            self.collocates = collocation(word, yearfrom=period[0], yearto = period[1], before=before, after=after,
                                corpus=corpus, limit=word_samples)
            self.collocates.columns = [word]
            if type(reference) is pandas.core.frame.DataFrame:
                reference = reference
            elif type(reference) is int:
                reference = get_corpus(yearfrom=period[0], yearto=period[1], corpus=corpus, samplesize=reference)
            else:
                reference = get_corpus(yearfrom=period[0], yearto=period[1], corpus=corpus, samplesize=int(reference))

            self.reference = aggregate(reference)
            self.reference.columns = ['reference_corpus']        
            self.word = word
            self.period = period
            self.corpus = corpus
        else:
            if filename != '':
                self.load(filename)
            
                
    def cluster_set(self, exponent=1.1, top = 200, aslist=True):
        combo_corp = self.reference.join(self.collocates, how='outer')
        normalize_corpus_dataframe(combo_corp)
        korpus = compute_assoc(combo_corp, self.word, exponent)
        korpus.columns = [self.word]
        if top <= 0:
            res = korpus.sort_values(by=self.word, ascending=False)
        else:
            res = korpus.sort_values(by=self.word, ascending=False).iloc[:top]
        if aslist == True:
            res = HTML(', '.join(list(res.index)))
        return res
    
    def add_reference(self, number=20):
        ref = get_corpus(yearfrom=self.period[0], yearto=self.period[1], samplesize=number)
        ref = aggregate(ref)
        ref.columns = ['add_ref']
        normalize_corpus_dataframe(ref)
        self.reference = aggregate(self.reference.join(ref, how='outer'))
        return True
    
    def save(self, filename=''):
        if filename == '':
            filename = "{w}_{p}-{q}.json".format(w=self.word,p=self.period[0], q = self.period[1])
        model = {
            'word':self.word,
            'period':self.period,
            'reference':self.reference.to_dict(),
            'collocates':self.collocates.to_dict(),
            'corpus':self.corpus
        }
        with open(filename, 'w', encoding = 'utf-8') as outfile:
            print('lagrer til:', filename)
            outfile.write(json.dumps(model))
        return True

    def load(self, filename):
        with open(filename, 'r') as infile:
            try:
                model = json.loads(infile.read())
                #print(model['word'])
                self.word = model['word']
                self.period = model['period']
                self.corpus = model['corpus']
                self.reference = pd.DataFrame(model['reference'])
                self.collocates = pd.DataFrame(model['collocates'])
            except:
                print('noe gikk galt')
        return True
    
       
    def search_words(self, words, exponent=1.1):
        if type(words) is str:
            words = [w.strip() for w in words.split()]
        df = self.cluster_set(exponent=exponent, top=0, aslist=False)
        sub= [w for w in words if w in df.index]
        res = df.transpose()[sub].transpose().sort_values(by=df.columns[0], ascending=False)
        return res


def wildcardsearch(params=None):
    if params is None:
        params = {'word': '', 'freq_lim': 50, 'limit': 50, 'factor': 2}
    res = requests.get('https://api.nb.no/ngram/wildcards', params=params)
    if res.status_code == 200:
        result = res.json()
    else:
        result = {'status':'feil'}
    resultat = pd.DataFrame.from_dict(result, orient='index')
    if not(resultat.empty):
        resultat.columns = [params['word']]
    return resultat

def sorted_wildcardsearch(params):
    res = wildcardsearch(params)
    if not res.empty:
        res = res.sort_values(by=params['word'], ascending=False)
    return res
            
def make_newspaper_network(key, wordbag, titel='%', yearfrom='1980', yearto='1990', limit=500):
    import networkx as nx
    if type(wordbag) is str:
        wordbag = wordbag.split()
    r = requests.post("https://api.nb.no/ngram/avisgraph", json={
        'key':key, 
        'words':wordbag,
        'yearto':yearto,
    'yearfrom':yearfrom,
    'limit':limit})
    G = nx.Graph()
    if r.status_code == 200:
        G.add_weighted_edges_from([(x,y,z) for (x,y,z) in r.json() if z > 0 and x != y])
    else:
        print(r.text)
    return G

def make_network(urn, wordbag, cutoff=0):
    if type(urn) is list:
        urn = urn[0]
    if type(wordbag) is str:
        wordbag = wordbag.split()
    G = make_network_graph(urn, wordbag, cutoff)
    return G

def make_network_graph(urn, wordbag, cutoff=0):
    import networkx as nx
    
    r = requests.post("https://api.nb.no/ngram/graph", json={'urn':urn, 'words':wordbag})
    G = nx.Graph()
    G.add_weighted_edges_from([(x,y,z) for (x,y,z) in r.json() if z > cutoff and x != y])
    return G

def draw_graph_centrality(G, h=15, v=10, fontsize=20, k=0.2, arrows=False, font_color='black', threshold=0.01): 
    from pylab import rcParams
    import matplotlib.pyplot as plt
    
    node_dict = nx.degree_centrality(G)
    subnodes = dict({x:node_dict[x] for x in node_dict if node_dict[x] >= threshold})
    x, y = rcParams['figure.figsize']
    rcParams['figure.figsize'] = h, v
    pos =nx.spring_layout(G, k=k)
    ax = plt.subplot()
    ax.set_xticks([])
    ax.set_yticks([])
    G = G.subgraph(subnodes)
    nx.draw_networkx_labels(G, pos, font_size=fontsize, font_color=font_color)
    nx.draw_networkx_nodes(G, pos, alpha=0.5, nodelist=subnodes.keys(), node_size=[v * 1000 for v in subnodes.values()])
    nx.draw_networkx_edges(G, pos, alpha=0.7, arrows=arrows, edge_color='lightblue', width=1)

    rcParams['figure.figsize'] = x, y
    return True

def combine(clusters):
    """Make new collocation analyses from data in clusters"""
    colls = []
    collocates = clusters[0].collocates
    for c in clusters[1:]:
        collocates = collocates.join(c.collocates, rsuffix='-' + str(c.period[0]))
    return collocates

def cluster_join(cluster):
    clusters = [cluster[i] for i in cluster]
    clst = clusters[0].cluster_set(aslist=False)
    for c in clusters[1:]:
        clst = clst.join(c.cluster_set(aslist=False), rsuffix = '_'+str(c.period[0]))
    return clst

def serie_cluster(word, startår, sluttår, inkrement, before=5, after=5, reference=150, word_samples=500):
    tidscluster = dict()
    for i in range(startår, sluttår, inkrement):
        tidscluster[i] = Cluster(
        word, 
        corpus='avis', 
        period=(i, i + inkrement - 1), 
        before=after, 
        after=after, 
        reference=reference, 
        word_samples=word_samples)
        print(i, i+inkrement - 1)
    return tidscluster

def save_serie_cluster(tidscluster):
    for i in tidscluster:
        tidscluster[i].save()
    return 'OK'

def les_serie_cluster(word, startår, sluttår, inkrement):
    tcluster = dict()
    for i in range(startår, sluttår, inkrement):
        print(i, i+inkrement - 1)
        tcluster[i] = Cluster(filename='{w}_{f}-{t}.json'.format(w=word, f=i,t=i+inkrement - 1))
    return tcluster




def make_cloud(json_text, top=100, background='white', stretch=lambda x: 2**(10*x), width=500, height=500, font_path=None):
    from collections import Counter
    pairs0 = Counter(json_text).most_common(top)
    pairs = {x[0]:stretch(x[1]) for x in pairs0}
    wc = WordCloud(
    font_path=font_path,  
    background_color=background,
    width=width, 
    #color_func=my_colorfunc,
    ranks_only=True,
    height=height).generate_from_frequencies(pairs)
    return wc

def draw_cloud(sky, width=20, height=20, fil=''):
    from matplotlib import pyplot as plt
    plt.figure(figsize=(width,height))
    plt.imshow(sky, interpolation='bilinear')
    figplot = plt.gcf()
    if fil != '':
        figplot.savefig(fil, format='png')
    return 

def cloud(pd, column='', top=200, width=1000, height=1000, background='black', file='', stretch=10, font_path=None):
    import json
    if column == '':
        column = pd.columns[0]
    data = json.loads(pd[column].to_json())
    a_cloud = make_cloud(data, top=top, 
                         background=background, font_path=font_path, 
                         stretch=lambda x: 2**(stretch*x), width=width, height=height)
    draw_cloud(a_cloud, fil=file)
    return


def make_a_collocation(word, period=(1990, 2000), before=5, after=5, corpus='avis', samplesize=100, limit=2000):
    collocates = collocation(word, yearfrom=period[0], yearto=period[1], before=before, after=after,
                             corpus=corpus, limit=limit)
    collocates.columns = [word]
    reference = get_corpus(yearfrom=period[0], yearto=period[1], samplesize=samplesize)
    ref_agg = aggregate(reference)
    ref_agg.columns = ['reference_corpus']
    return  ref_agg



def compute_assoc(coll_frame, column, exponent=1.1, refcolumn = 'reference_corpus'):
    return pd.DataFrame(coll_frame[column]**exponent/coll_frame.mean(axis=1))
    

class Corpus:
    from IPython.display import HTML, display
    import pandas as pd
    import json
    
    def __init__(self, filename = '', period = (1950,1960), author='%', 
                 title='%', ddk='%', gender='%', subject='%', reference = 100, max_books=100):
        import pandas
        import random
        
        params = {
            'year':period[0], 
            'next': period[1]-period[0], 
            'subject':subject,
            'ddk':ddk, 
            'author':author, 
            #'gender':gender, ser ikke ut til å virke for get_urn - sjekk opp APIet
            'title':title, 
            'limit':max_books,
            'reference':reference
        }
        self.params = params
        
        if filename == '':
            målkorpus_def = get_urn(params)

            #print("Antall bøker i målkorpus ", len(målkorpus_def))
            målkorpus_urn = [x[0] for x in målkorpus_def]
            if len(målkorpus_urn) > max_books:
                target_urn = random.sample(målkorpus_urn,max_books)
            else:
                target_urn = målkorpus_urn
                
            if type(reference) is pandas.core.frame.DataFrame:
                reference = reference 
            else:
                referansekorpus_def = get_urn({'year':period[0], 'next':period[1]-period[0], 'limit':reference})
 
                              
            #print("Antall bøker i referanse: ", len(referansekorpus_def))
            referanse_urn = [x[0] for x in referansekorpus_def]
            self.reference_urn = referanse_urn
            self.target_urn = target_urn
            # make sure there is no overlap between target and reference
            referanse_urn = list(set(referanse_urn) - set(target_urn))
            
            referanse_txt = get_corpus_text(referanse_urn)
            målkorpus_txt = get_corpus_text(target_urn)
            
            normalize_corpus_dataframe(referanse_txt)
            normalize_corpus_dataframe(målkorpus_txt)
            
            combo = målkorpus_txt.join(referanse_txt)
            
            #self.combo = combo 
            #self.reference = referanse_txt
            #self.target = målkorpus_txt
 
            #self.reference = aggregate(reference)
            #self.reference.columns = ['reference_corpus']
            
            ## dokumentfrekvenser
            
            mål_docf = pd.DataFrame(pd.DataFrame(målkorpus_txt/målkorpus_txt).sum(axis=1))
            combo_docf = pd.DataFrame(pd.DataFrame(combo/combo).sum(axis=1))
            ref_docf = pd.DataFrame(pd.DataFrame(referanse_txt/referanse_txt).sum(axis=1))

            ### Normaliser dokumentfrekvensene
            normalize_corpus_dataframe(mål_docf)
            normalize_corpus_dataframe(combo_docf)
            #normalize_corpus_dataframe(ref_docf)
            
            self.målkorpus_tot = aggregate(målkorpus_txt)
            self.combo_tot = aggregate(combo)
            self.mål_docf = mål_docf
            self.combo_docf = combo_docf
            
        else:
            self.load(filename)
            
                
    def difference(self, freq_exp=1.1, doc_exp=1.1, top = 200, aslist=True):
        res = pd.DataFrame(
            (self.målkorpus_tot**freq_exp/self.combo_tot)*(self.mål_docf**doc_exp/self.combo_docf)
        )
        res.columns = ['diff']
        if top > 0:
            res = res.sort_values(by=res.columns[0], ascending=False).iloc[:top]
        else:
            res = res.sort_values(by=res.columns[0], ascending=False)
        if aslist == True:
            res = HTML(', '.join(list(res.index)))
        return res
    

    def save(self, filename):
        model = {
            'params':self.params,   
            'target': self.målkorpus_tot.to_json(),
            'combo': self.combo_tot.to_json(),
            'target_df': self.mål_docf.to_json(),
            'combo_df': self.combo_docf.to_json()
        }

        with open(filename, 'w', encoding = 'utf-8') as outfile:
            outfile.write(json.dumps(model))
        return True

    def load(self, filename):
        with open(filename, 'r') as infile:
            try:
                model = json.loads(infile.read())
                #print(model['word'])
                self.params = model['params']
                #print(self.params)
                self.målkorpus_tot = pd.read_json(model['target'])
                #print(self.målkorpus_tot[:10])
                self.combo_tot = pd.read_json(model['combo'])
                self.mål_docf = pd.read_json(model['target_df'])
                self.combo_docf = pd.read_json(model['combo_df'])
            except:
                print('noe gikk galt')
        return True
    
    def summary(self, head=10):
        info = {
            'parameters':self.params,
            'target_urn':self.target_urn[:head],
            'reference urn':self.reference_urn[:head],
            
        }
        return info

    def search_words(self, words, freq_exp=1.1, doc_exp=1.1):
        if type(words) is str:
            words = [w.strip() for w in words.split()]
        df = self.difference(freq_exp = freq_exp, doc_exp=doc_exp,top=0, aslist=False)
        sub = [w for w in words if w in df.index]
        res = df.transpose()[sub].transpose().sort_values(by=df.columns[0], ascending=False)
        return res
            
        
def vekstdiagram(urn, params=None):
    import requests
    import pandas as pd
    
    if params is None:
        params = {}

    # if urn is the value of get_urn() it is a list
    # otherwise it just passes
    if type(urn) is list:
        urn = urn[0]
    
    para = params
    para['urn']= urn
    r = requests.post('https://api.nb.no/ngram/vekstdiagram', json = para)
    return pd.DataFrame(r.json())

def plot_sammen_vekst(urn, ordlister, window=5000, pr = 100):
    """Plott alle seriene sammen"""
    rammer = []
    for ordbag in ordlister:
        vekst = vekstdiagram(urn, params = {'words': ordbag, 'window':window, 'pr': pr} )
        vekst.columns = [ordbag[0]]
        rammer.append(vekst)
    return pd.concat(rammer)

def relaterte_ord(word, number = 20, score=False):
    import networkx as nx
    from networkx.algorithms import community
    
    G = make_graph(word)
    res = Counter(nx.eigenvector_centrality(G)).most_common(number) 
    if score == False:
        res = [x[0] for x in res]
    return res


def check_words(urn, ordbag):
    if type(urn) is list:
        urn = urn[0]
    ordliste = get_freq(urn, top=50000, cutoff=0)
    res = Counter()
    for w in ordbag:
        res[w] = ordliste[w]
    for p in res.most_common():
        if p[1] != 0:
            print(p[0], p[1])
        else:
            break
    return True

def nb_ngram(terms, corpus='bok', smooth=3, years=(1810, 2010), mode='relative'):
    return ngram_conv(get_ngram(terms, corpus=corpus), smooth=smooth, years=years, mode=mode)
    
def get_ngram(terms, corpus='avis'):
    req = requests.get(
        "http://www.nb.no/sp_tjenester/beta/ngram_1/ngram/query?terms={terms}&corpus={corpus}".format(
            terms=terms,
            corpus=corpus
        ))
    if req.status_code == 200:
        res = req.text
    else:
        res = "[]"
    return json.loads(res)

def ngram_conv(ngrams, smooth=1, years=(1810,2013), mode='relative'):
    ngc = {}
    # check if relative frequency or absolute frequency is in question
    if mode.startswith('rel') or mode=='y':
        arg = 'y'
    else:
        arg = 'f'
    for x in ngrams:
        if x != []:
            ngc[x['key']] = {z['x']:z[arg] for z in x['values'] if int(z['x']) <= years[1] and int(z['x']) >= years[0]}
    return pd.DataFrame(ngc).rolling(window=smooth, win_type='triang').mean()


def make_graph(word):
    result = requests.get("https://www.nb.no/sp_tjenester/beta/ngram_1/galaxies/query?terms={word}".format(word=word))
    G = nx.DiGraph()
    edgelist = []
    if result.status_code == 200:
        graph = json.loads(result.text)
        #print(graph)
        nodes = graph['nodes']
        edges = graph['links']
        for edge in edges:
            edgelist += [(nodes[edge['source']]['name'], nodes[edge['target']]['name'], abs(edge['value']))]
    #print(edgelist)
    G.add_weighted_edges_from(edgelist)
    return G


def get_konk(word, params=None, kind='html'):
    import requests
    import pandas as pd

    if params is None:
        params = {}

    para = params
    para['word']= word

    corpus = 'bok'
    if 'corpus' in para:
        corpus = para['corpus']
    else:
        para['corpus'] = corpus
        
    r = requests.get('https://api.nb.no/ngram/konk', params=para)
    if kind=='html':
        rows = ""
        row_template = ("<tr>"
                        "<td><a href='{urn}' target='_'>{urnredux}</a></td>"
                        "<td>{b}</td>"
                        "<td>{w}</td>"
                        "<td style='text-align:left'>{a}</td>"
                        "</tr>\n")
        if corpus == 'bok':
            for x in r.json():
                rows += row_template.format(
                    urn=x['urn'],
                    urnredux=','.join([x['author'], x['title'], str(x['year'])]),
                    b=x['before'],
                    w=x['word'],
                    a=x['after'])
        else:
            #print(r.json())
            for x in r.json():
                rows += row_template.format(
                    urn=x['urn'],
                    urnredux='-'.join(x['urn'].split('_')[2:6:3]),
                    b=x['before'],
                    w=x['word'],
                    a=x['after'])
        res = "<table>{rows}</table>".format(rows=rows)
        res = HTML(res)
    elif kind == 'json':
        res = r.json()
    else:
        try:
            if corpus == 'bok':
                res = pd.DataFrame(r.json())
                res = res[['urn','author','title','year','before','word','after']]
            else:
                res = pd.DataFrame(r.json())
                res = res[['urn','before','word','after']]
            
        except:
            res= pd.DataFrame()
        #r = r.style.set_properties(subset=['after'],**{'text-align':'left'})
    return res



def konk_to_html(jsonkonk):
    rows = ""
    row_template = ("<tr>"
                    "<td><a href='{urn}' target='_'>{urnredux}</a></td>"
                    "<td>{b}</td>"
                    "<td>{w}</td>"
                    "<td style='text-align:left'>{a}</td>"
                    "</tr>\n")
    for x in jsonkonk:
        rows += row_template.format(
            urn=x['urn'], urnredux=x['urn'], b=x['before'], w=x['word'], a=x['after'])
    res = "<table>{rows}</table>".format(rows=rows)
    return res

def central_characters(graph, n=10):
    import networkx as nx
    from collections import Counter
    
    res = Counter(nx.degree_centrality(graph)).most_common(n)
    return res

def central_betweenness_characters(graph, n=10):
    import networkx as nx
    from collections import Counter
    
    res = Counter(nx.betweenness_centrality(graph)).most_common(n)
    return res
    

def get_urnkonk(word, params=None, html=True):
    import requests
    import pandas as pd

    if params is None:
        params = {}

    para = params
    para['word']= word
    try:
        para['urns'] = pure_urn(para['urns'])
    except:
        print('Parameter urns missing')
    r = requests.post('https://api.nb.no/ngram/urnkonk', json = para)
    if html:
        rows = ""
        for x in r.json():
            rows += """<tr>
                <td>
                    <a href='{urn}' target='_blank' style='text-decoration:none'>{urnredux}</a>
                </td>
                <td>{b}</td>
                <td>{w}</td>
                <td style='text-align:left'>{a}</td>
            </tr>\n""".format(urn=x['urn'],
                              urnredux="{t}, {f}, {y}".format(t=x['title'], f=x['author'], y=x['year']),
                              b=x['before'],
                              w=x['word'],
                              a=x['after']
                             )
        res = """<table>{rows}</table>""".format(rows=rows)
        res = HTML(res)
    else:
        res = pd.DataFrame(r.json())
        res = res[['urn','before','word','after']]
        #r = r.style.set_properties(subset=['after'],**{'text-align':'left'})
    return res

def frame(something, name):
    res =  pd.DataFrame(something)
    res.columns = [name]
    return res
