# -*- coding: utf-8 -*-
"""
Iterates over the taxa listed in the NCBI Taxonomy database and creates
corresponding FluidInfo objects with the most relevant tags.

Uses the NCBI E-Utilities Esearch and Efetch:
*   http://www.ncbi.nlm.nih.gov/books/NBK25499/#chapter4.ESearch
*   http://www.ncbi.nlm.nih.gov/books/NBK25499/#chapter4.EFetch

This is kind of the core tool, since other scripts will later iterate over
those FluidInfo objects to perform other tasks.

For testing purposes, the list of imported taxa was first limited to just a few:
* TaxId: 9913  as about: bos taurus    with uid: 82b383ce-e42e-4d79-be6d-10d5283c5443
* TaxId: 9606  as about: homo sapiens  with uid: a1d5b1d2-8eef-450c-b772-b8e28ab58184

Currently it processes all the species of division primates, whose scientific names don't contain any digits.

"""


import sys
import os.path
import urllib
import urllib2

try:
    from xml.etree import cElementTree as ElementTree
except ImportError, e:
    from xml.etree import ElementTree
    
from fom.session import Fluid
from fom.mapping import Object, Namespace
from fom.errors import Fluid412Error
    

urlEutils = "http://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
urlEsearch = urlEutils + "esearch.fcgi"
urlEfetch = urlEutils + "efetch.fcgi"

def GetTaxonData(lTaxIds):
    """
        Given a list of NCBI-Taxonomy-IDs, it uses Efetch to get
        their Taxon data in a single request.
        
        Returns a list of ElementTrees, each rooted at the <Taxon> tag.
        
        Documentation of Efetch:
            http://www.ncbi.nlm.nih.gov/books/NBK25499/#chapter4.EFetch
        
        See example XML data at: 
            eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=taxonomy&id=9913,9606&mode=xml
    """
    # Request NCBI taxon data for the given ID list
    data = urllib.urlencode({ 'db'    : 'taxonomy'
                             ,'mode'  : 'xml'
                             ,'id'    : ','.join([str(iTax) for iTax in lTaxIds]) })
    # print data
    tree = ElementTree.parse(urllib2.urlopen(urlEfetch, data ))
    # tree.write(sys.stdout)
    # Beware to match only <Taxon> items at the
    # first level, but not the ones inside <LineageEx> !
    elTaxon = tree.findall('Taxon') 
    assert(len(elTaxon) == len(lTaxIds))
    return elTaxon



class iterTaxa:
    """Forward iterator for Taxonomy query results.
    
       Given a query-term, it allows to iterate one by one though the
       query-matches, returning those as ElementTrees containing all available NCBI-data for a Taxon.
       
       Takes care internally to request data in large chunks, instead of one by one.
       Only forward iterator.
    
       NCBI Esearch Documentation at:
           http://www.ncbi.nlm.nih.gov/books/NBK25499/#chapter4.ESearch

        @param term:        Query term using Entrez syntax operating on NCBI-Taxonomy database.
                            Examples:
                                "species[Rank] AND PRI[TXDV]"
                                "species[Rank] AND (9913[UID] OR 9606[UID])"
                                
                            Obtain full list of available field and index names, by querying Einfo:
                                http://eutils.ncbi.nlm.nih.gov/entrez/eutils/einfo.fcgi?db=taxonomy    
                            
                            Bloated documentation here:
                                http://www.ncbi.nlm.nih.gov/books/NBK3837/#EntrezHelp.Indexed_Fields_Query_Translat
                            
        @param chunksize:   Number of results per API-query. Defaults to 20. Those are cached and iterated one by one
    """
    def __init__(self, term, chunksize=20):
        self.term = term
        self.chunksize = chunksize
        self.start = 0
        self.count = 0
        self.cache = []
        
    def GetNextChunk(self):
        """
            Get the chunk of results that starts at retstart=self.start
        """
        data = urllib.urlencode({ 'db'      : 'taxonomy'
                                 ,'term'    : self.term
                                 ,'retstart': self.start
                                 ,'retmax'  : self.chunksize  })
        #print "Debug: ", data
        tree = ElementTree.parse(urllib2.urlopen(urlEsearch, data ))
        #tree.write(sys.stdout)
        
        # Extract the TaxId values
        lTaxIds = [int(id.text) for id in tree.findall("IdList/Id")]
        # If we got any TaxIds, then we'll Efetch the corresponding Taxon data
        # in a chunk as big as the one returned by Esearch.
        if len(lTaxIds):
            self.cache = GetTaxonData(lTaxIds)
            self.count = int(tree.find("Count").text)
        
        
    def GetNext(self):
        """
            Get the next Taxon that matches the query.
            Returns None if there are no matches left.
        """
        if (len(self.cache)==0):
            self.GetNextChunk()
                
        if (len(self.cache)):
            self.start += 1
            return self.cache.pop(0)
        else:
            return None
        
    def GetFirst(self):
        """
            Get the first Taxon that matches the query.
            Returns None if query didn't match or succeed.
        """
        self.start = 0
        del self.cache[:]
        return self.GetNext()



            
def ImportTaxonAttribute(dictTagging, xmlTaxonData, sAttrName, typecast=unicode, aslist=False, sTagName=None ):
    """
        Does the actual transfer of values from the XML into FluidInfo tags.
        It actually doesn't tag yet, but it transfers the data into a dict(), which will later be used to do the taggin in a single API request.
        
        @note It prepends the tag-path in sUserNS to the tags to be imported. sUserNS is currently just the user-namespace.
        
        @param dictTagging: [out] A dict[u'tagpath']=tagvalue for the object of the taxon we are dealing with.

        @param xmlTaxonData: An ElementTree containing the <Taxon> XML branch sent by NCBI.
                             See example XML: eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=taxonomy&id=9913&mode=xml

        @param sAttrName: String with XPath to the item that should be transferred. 
                          Root is at <Taxon>. 
                          e.g. To get the TaxId use sAttrName="TaxId"
                          
        @param typecast: Python data type for the XML string to be casted to.
                         Defaults to unicode.
                         e.g. typecast=int
                         
        @param aslist: Boolean. 
                       If False (the default), then sAttrName should yield only a single XML item that will be treated as a scalar.
                       If True, then all the items referred by sAttrName will be assembled into a list/set.

        @param sTagName: The FluidInfo tag path  (relative to the prefix sUserNS).
                         Defaults to the XPath given in sAttrName.
                          
    """
    
    elAttr = xmlTaxonData.findall(sAttrName)

    if (sTagName is None):
        sTagName = sAttrName
        
    if aslist:
        ValueList = [typecast(item.text.strip()) for item in elAttr]
        if len(ValueList)>0:
            dictTagging[sUserNS+u"/taxonomy/ncbi/"+sTagName] =  ValueList
    else:
        assert( len(elAttr)<2 )
        if len(elAttr)==1:
            dictTagging[sUserNS+u"/taxonomy/ncbi/"+sTagName] = typecast(elAttr[0].text)
        
        
def containsAny(str, set):
    """Check whether 'str' contains ANY of the chars in 'set'"""
    return 1 in [c in str for c in set]
    
def ImportTaxon(xmlTaxonData):
    """
        Imports a "NCBI Taxonomy" record from a XML <Taxon> tree into FluidInfo.
        
        Warning: Heavy work in progress!
    """

    assert( xmlTaxonData is not None)
    
    ScientificName = unicode(xmlTaxonData.find("ScientificName").text)

    dictTagging = dict()
    
    # WARNING: For the time being, we'll discard any unusual taxa with digits in their scientific names.
    if containsAny(ScientificName, '0123456789:'):
        print "Not importing weird taxon:", ScientificName
        return

    # Assign about tag value. Lowercase!
    sAbout = ScientificName.lower()

    ImportTaxonAttribute(dictTagging, xmlTaxonData, "ScientificName", typecast=unicode)
    ImportTaxonAttribute(dictTagging, xmlTaxonData, "TaxId", typecast=int)
    ImportTaxonAttribute(dictTagging, xmlTaxonData, "ParentTaxId", typecast=int)
    ImportTaxonAttribute(dictTagging, xmlTaxonData, "Rank", typecast=unicode)
    ImportTaxonAttribute(dictTagging, xmlTaxonData, "Division", typecast=unicode)
    ImportTaxonAttribute(dictTagging, xmlTaxonData, "OtherNames/GenbankCommonName", typecast=unicode, sTagName=u"GenbankCommonName")
    
    ImportTaxonAttribute(dictTagging, xmlTaxonData, "OtherNames/Synonym", typecast=unicode, aslist=True, sTagName=u"Synonyms")
    ImportTaxonAttribute(dictTagging, xmlTaxonData, "OtherNames/CommonName", typecast=unicode, aslist=True, sTagName=u"CommonNames")
    
    ImportTaxonAttribute(dictTagging, xmlTaxonData, "LineageEx/Taxon/ScientificName", typecast=unicode, aslist=True, sTagName=u"Lineage")
    # NOTE: FluidInfo only implements "sets of strings". There is not support for "sets of integers"!
    ImportTaxonAttribute(dictTagging, xmlTaxonData, "LineageEx/Taxon/TaxId", typecast=unicode, aslist=True, sTagName=u"LineageIds")
    
    # TODO: Query for LinkOut data and add info to this object
    #       Most wanted are Wikipedia ArticleIDs provided by iPhylo:
    #           http://eutils.ncbi.nlm.nih.gov/entrez/eutils/elink.fcgi?dbfrom=taxonomy&id=9606&cmd=llinks&holding=iPhylo
    #       Beware that there are several LinkOut items provided by iPhylo!! We want those containing:
    #           <LinkName>Wikipedia</LinkName>
    #       Translate ArticleId into Wikipedia Title with:
    #           http://en.wikipedia.org/w/api.php?action=query&pageids=682482&format=xml
    #           more info on  http://www.mediawiki.org/wiki/API


    ##################################
    # Create and do all the tagging in
    # a single call to the FluidInfo-API!
    ##
    # Convert into the cumbersome dict in dict format needed by the values.put() API
    ddValues = dict()
    for tagpath, tagvalue in dictTagging.items():
        dictTmp = dict()
        dictTmp[u'value'] = tagvalue
        ddValues[tagpath] = dictTmp
        
    #    import pprint
    #    pprint.pprint(ddValues)
    fdb.values.put( query='fluiddb/about = "'+sAbout+'"',values=ddValues)
    
    print "Imported TaxId:", dictTagging[sUserNS+u'/taxonomy/ncbi/TaxId'], " as about:",sAbout # , " with uid:", oTaxon.uid

    


    
if __name__ == "__main__":

    #############################
    # Bind to FluidInfo instance
    fileCredentials = open(os.path.expanduser('~/.fluidDBcredentials'), 'r')
    username = fileCredentials.readline().strip()
    password = fileCredentials.readline().strip()
    fileCredentials.close()
    # fdb = Fluid('https://sandbox.fluidinfo.com')  # The sandbox instance
    fdb = Fluid()  # The main instance
    fdb.login(username, password)
    fdb.bind()
    nsUser = Namespace(username)
    
    sUserNS = nsUser.path     # Ugly use of a global, I know. :-)

    # We aren't ready yet to import all the 800k+ taxons of the NCBI database, so meanwhile
    # we use additonal query criteria to limit the result to just a few items!!

    # Import all primate species:
    itSpecies = iterTaxa(term="species[Rank] AND PRI[TXDV]", chunksize=100)

    # Import just two species: Bos taurus, Homo sapiens
    # itSpecies = iterEsearch("species[Rank] AND (9913[UID] OR 9606[UID])")


    xmlTaxonData = itSpecies.GetFirst()
    print "Total number of results: ", itSpecies.count

    while xmlTaxonData is not None:
        ImportTaxon(xmlTaxonData)
        xmlTaxonData = itSpecies.GetNext()
        
        
    # Put some usefull info on the description-tag of the namespace objects.
    Namespace(sUserNS+u'/taxonomy')._set_description( u'Data imported by the fiTaxonomy scripts found at https://github.com/axeloide/fiTaxonomy')
    Namespace(sUserNS+u'/taxonomy/ncbi')._set_description( u'Data extracted from the "NCBI Taxonomy" database.')

