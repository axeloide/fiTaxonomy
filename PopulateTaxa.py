# -*- coding: utf-8 -*-
"""
Uses the NCBI E-Utilities API to iterate over taxa and import their records into FluidInfo.

A testbench for @axeloide's thoughts about leveraging FluidInfo to get difficult data into a more usable representation.

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
from fom.mapping import Object, Namespace, Tag
from fom.errors import Fluid412Error
    

urlEutils = "http://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
urlEsearch = urlEutils + "esearch.fcgi"
urlEfetch = urlEutils + "efetch.fcgi"
urlElink = urlEutils + "elink.fcgi"




class iterEsearch:
    """Forward iterator for Esearch query results.
    
       Iterates one by one through the ID's that matched a Esearch query.
       Only forward iterator.
    
       NCBI Esearch Documentation at:
           http://www.ncbi.nlm.nih.gov/books/NBK25499/#chapter4.ESearch

        @param db:          Database name as listed by http://eutils.ncbi.nlm.nih.gov/entrez/eutils/einfo.fcgi
                            e.g.: "taxonomy", 
                        
        @param term:        Query term using Entrez syntax.
                            Bloated documentation here:
                                http://www.ncbi.nlm.nih.gov/books/NBK3837/#EntrezHelp.Indexed_Fields_Query_Translat
                            
        @param chunksize:   Number of results per API-query. Defaults to 20. Those are cached and iterated one by one
    """
    def __init__(self, db, term, chunksize=20):
        self.db = db
        self.term = term
        self.chunksize = chunksize
        self.start = 0
        self.count = 0
        self.cache = []
        
    def GetNextChunk(self):
        """
            Get the chunk of results that starts at retstart=self.start
        """
        data = urllib.urlencode({ 'db'      : self.db
                                 ,'term'    : self.term
                                 ,'retstart': self.start
                                 ,'retmax'  : self.chunksize  })
        #print "Debug: ", data
        tree = ElementTree.parse(urllib2.urlopen(urlEsearch, data ))
        #tree.write(sys.stdout)
        self.count = int(tree.find("Count").text)
        self.cache = [int(id.text) for id in tree.findall("IdList/Id")]
        
    def GetNext(self):
        """
            Get the next ID.
            Returns None if there is no ID left.
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
            Get the next ID.
            Returns None if query didn't match or succeed.
        """
        self.start = 0
        del self.cache[:]
        return self.GetNext()


def GetTaxonData(idTax):
    """
        Uses Efetch to get the whole Taxon record for a given NCBI-Taxonomy-ID.
        Returns an ElementTree with root at the <Taxon> tag.
        
        See example XML data at: 
            eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=taxonomy&id=9913&mode=xml
    """
    # Request NCBI taxon data for the given ID
    data = urllib.urlencode({ 'db'    : 'taxonomy'
                             ,'mode': 'xml'
                             ,'id'    : idTax })
    # print data
    tree = ElementTree.parse(urllib2.urlopen(urlEfetch, data ))
    # tree.write(sys.stdout)
    elTaxon = tree.findall('Taxon') # Beware not to match the <Taxon> items inside <LineageEx> !
    assert(len(elTaxon) == 1)
    return elTaxon[0]

def SplitSemicolonDelimitedString(sString):
    """
        Used as "typecast" parameter on strings that should be splitted into set of unicode strings into FluidInfo
    """
    return [ uStr.strip().lower() for uStr in unicode(sString).split(";")]
            
def ImportTaxonAttribute(oTaxon, xmlTaxonData, sAttrName, typecast=unicode, aslist=False, sTagName=None ):
    """
        Does the actual transfer of values from the XML into FluidInfo tags.
        
        @note It prepends the tag-path in sRoot to the tags to be imported. sRoot is currently just the user-namespace.
        
        @param oTaxon: The FOM object of the taxon we are dealing with.

        @param xmlTaxonData: An ElementTree containing the <Taxon> XML branch sent by NCBI.
                             See example XML: eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=taxonomy&id=9913&mode=xml

        @param sAttrName: String with XPath to the item that should be transferred. 
                          Root is at <Taxon>. 
                          e.g. To get the TaxId use sAttrName="TaxId"
                          
        @param typecast: Python data type for the XML string to be casted to.
                         Defaults to unicode.
                         e.g. typecast=int
                         
        @param aslist: Boolean. 
                       If False, then sAttrName should yield only a single XML item that will be treated as a scalar.
                       If True, then all the items referred by sAttrName will be assembled into a list/set.
                       TODO: In some cases we will want to get a e.g. semicolon delimited string and split it into a list/set!

        @param sTagName: The FluidInfo (relative) tag path.
                         Defaults to the XPath given in sAttrName.
                          
    """
    
    elAttr = xmlTaxonData.findall(sAttrName)

    if (sTagName is None):
        sTagName = sAttrName
        
    if aslist:
        ValueList = [typecast(item.text.strip()) for item in elAttr]
        oTaxon.set(sRoot+u"/taxonomy/ncbi/"+sTagName, ValueList)
    else:
        assert(len(elAttr) == 1)
        oTaxon.set(sRoot+u"/taxonomy/ncbi/"+sTagName, typecast(elAttr[0].text))
        

    
def ImportTaxonById(TaxId):
    """
        Imports a "NCBI Taxonomy" record for a given TaxonomyID into FluidInfo.
        
        Warning: Heavy work in progress!
    """
    xmlTaxonData = GetTaxonData(TaxId)
    assert( xmlTaxonData is not None)
    assert( TaxId == int(xmlTaxonData.find("TaxId").text))
    
    # Assign about tag value
    ScientificName = xmlTaxonData.find("ScientificName").text
    oTaxon = Object(about=ScientificName.lower())

    ImportTaxonAttribute(oTaxon, xmlTaxonData, "ScientificName", typecast=unicode)
    ImportTaxonAttribute(oTaxon, xmlTaxonData, "TaxId", typecast=int)
    ImportTaxonAttribute(oTaxon, xmlTaxonData, "ParentTaxId", typecast=int)
    ImportTaxonAttribute(oTaxon, xmlTaxonData, "Rank", typecast=unicode)
    ImportTaxonAttribute(oTaxon, xmlTaxonData, "Division", typecast=unicode)
    ImportTaxonAttribute(oTaxon, xmlTaxonData, "OtherNames/GenbankCommonName", typecast=unicode, sTagName=u"GenbankCommonName")
    
    ImportTaxonAttribute(oTaxon, xmlTaxonData, "OtherNames/Synonym", typecast=unicode, aslist=True, sTagName=u"Synonyms")
    ImportTaxonAttribute(oTaxon, xmlTaxonData, "OtherNames/CommonName", typecast=unicode, aslist=True, sTagName=u"CommonNames")
    
    ImportTaxonAttribute(oTaxon, xmlTaxonData, "Lineage", typecast=SplitSemicolonDelimitedString)
    # NOTE: FluidInfo only implements "sets of strings". There is not support for "sets of integers"!
    ImportTaxonAttribute(oTaxon, xmlTaxonData, "LineageEx/Taxon/TaxId", typecast=unicode, aslist=True, sTagName=u"LineageIds")
    
    # TODO: Query for LinkOut data and add info to this object
    #       Most wanted are Wikipedia ArticleIDs provided by iPhylo:
    #           http://eutils.ncbi.nlm.nih.gov/entrez/eutils/elink.fcgi?dbfrom=taxonomy&id=9606&cmd=llinks&holding=iPhylo
    #       Beware that there are several LinkOut items provided by iPhylo!! We want those containing:
    #           <LinkName>Wikipedia</LinkName>
    #       Translate ArticleId into Wikipedia Title with:
    #           http://en.wikipedia.org/w/api.php?action=query&pageids=682482&format=xml
    #           more info on  http://www.mediawiki.org/wiki/API

    oTaxon.save()
    print "Imported TaxId:", TaxId, " as about:",oTaxon.about, " with uid:", oTaxon.uid

    


    
if __name__ == "__main__":

    #############################
    # Bind to FluidInfo instance
    fileCredentials = open(os.path.expanduser('~/.fluidDBcredentials'), 'r')
    username = fileCredentials.readline().strip()
    password = fileCredentials.readline().strip()
    fileCredentials.close()
    # session = Fluid('https://sandbox.fluidinfo.com')  # The sandbox instance
    session = Fluid()  # The main instance
    session.login(username, password)
    session.bind()
    nsRoot = Namespace(username)
    
    sRoot = nsRoot.path     # Ugly use of a global, I know. :-)


    # We aren't ready yet to import all the 800k+ taxons of the NCBI database, so meanwhile
    # we use additonal query criteria to limit the result to just a few items!!

    # Import all primate species:   itSpecies = iterEsearch('taxonomy', "species[Rank] AND PRI[TXDV]")

    # Import just a single species: Bos taurus = cattle    
    itSpecies = iterEsearch('taxonomy', "species[Rank] AND (9913[UID] OR 9606[UID])")


    idSpecies = itSpecies.GetFirst()
    print "Total number of results: ", itSpecies.count

    while idSpecies is not None:
        ImportTaxonById(idSpecies)
        idSpecies = itSpecies.GetNext()

