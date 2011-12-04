# -*- coding: utf-8 -*-
"""
PopulateLinkOut.py

Iterates over all FluidInfo objects with a ./taxonomy/ncbi/TaxId tag and
uses the NCBI E-Utility Elink to recreate a web of references to related
objects/datasources in FluidInfo, creating and populating those where necessary.

http://www.ncbi.nlm.nih.gov/books/NBK25499/#chapter4.ELink

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
from fom.mapping import Object, Namespace, tag_value
from fom.errors import Fluid412Error
    

urlEutils = "http://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
urlElink = urlEutils + "elink.fcgi"

urlWikipediaApi="http://en.wikipedia.org/w/api.php"


def GetLinkOutData(idTax):
    """
        Uses Elink to get the LinkOut data for a given NCBI-Taxonomy-ID:
        Returns an ElementTree with root at the <IdUrlSet> tag.
        
        http://www.ncbi.nlm.nih.gov/books/NBK25499/#chapter4.ELink
        
        See example XML data at: 
            http://eutils.ncbi.nlm.nih.gov/entrez/eutils/elink.fcgi?dbfrom=taxonomy&id=9482&cmd=llinks
    """
    # Request NCBI taxon data for the given ID
    data = urllib.urlencode({ 'dbfrom' : 'taxonomy'
                             ,'cmd'    : 'llinks'
                             ,'id'     : idTax
                             ,'holding'   : 'iPhylo' }) # WARNING: We are currently limiting this to just one provider, for testing purposes!
    # print data
    tree = ElementTree.parse(urllib2.urlopen(urlElink, data ))
    # tree.write(sys.stdout)
    eUrlSet = tree.find(u'LinkSet/IdUrlList/IdUrlSet')
    assert(eUrlSet is not None)
    return eUrlSet
    
def LookupWikipediaTitle(iArticleId):
    data = urllib.urlencode({ 'action' : 'query'
                             ,'format' : 'xml'
                             ,'pageids': iArticleId })
    # print data
    tree = ElementTree.parse(urllib2.urlopen(urlWikipediaApi, data ))
    # tree.write(sys.stdout)
    ePage = tree.find(u'query/pages/page')
    return ePage.attrib['title']

def HandleIPhyloLinks(oTaxon, elObjUrl):
    """
    """
    ###############################################
    # Check existance of Wikipedia LinkOut entry 
    # Provider is iPhylo, but it also provides links to "BBC Wildlife Finder"
    # WARNING: iPhylo links to the ArticleId on Wikipedia, so we have to do an
    #          additional lookup to convert it to the article title, as used in FluidInfo about tags.
    # XPath support on ElementTree is very limited, so we have to iterate over 
    # all items, to find the matching ones.
    for eObjUrl in elObjUrl:
        if (eObjUrl.find("Provider/Name").text == 'iPhylo'):
            if (eObjUrl.find("LinkName").text == 'Wikipedia'):
                # Extract the Wikipedia PageId/ArticleId from the url
                # TODO: The following line is so ugly!
                sWikiRawUrl = eObjUrl.find("Url").text
                iWikiPageId = int(sWikiRawUrl.split(u'=')[1])
                sWikiTitle = LookupWikipediaTitle(iWikiPageId)
                print "Jay! Found a Wikipedia link to ArticleID:",iWikiPageId," with title:",sWikiTitle
                oTaxon.set(sNcbiNS + u'/LinkOut/wikipedia', sWikiRawUrl)
                # Sometimes the iPhylo-linked Wikipedia Title doesn't match this Taxon's about value,
                # in such cases we add a "related-wikipedia" tag pointing to the iPhylo Wikipedia article.
                # Example: Taxon('homo sapiens') is linked by iPhylo to Wikipedia('Human')
                if (sWikiTitle.lower() != oTaxon.about):
                    oTaxon.set(sNcbiNS + u'/LinkOut/related-wikipedia', sWikiTitle.lower())
                oWP = WikipediaPage(about=sWikiTitle.lower())
                oWP.RelatedTaxon = oTaxon.about
                oWP.PageId = iWikiPageId
                oWP.save()

            elif (eObjUrl.find("LinkName").text == 'BBC Wildlife Finder'):
                sBbcUrl = eObjUrl.find("Url").text
                # TODO: The following line is so ugly!
                sBbcTitle = sBbcUrl.split(u'/')[-1]
                print "Jay! Found a BBC link:", sBbcUrl," with title:",sBbcTitle
                oTaxon.set(sNcbiNS + u'/LinkOut/bbcwildlife', sBbcUrl)
                # Sometimes the iPhylo-linked BBC Title doesn't match this Taxon's about value,
                # in such cases we add a "related-bbcwildlife" tag pointing to the iPhylo BBC article.
                # Example: Taxon('homo sapiens') is linked by iPhylo to BBC('Human')
                if (sBbcTitle.lower() != oTaxon.about):
                    oTaxon.set(sNcbiNS + u'/LinkOut/related-bbcwildlife', sBbcTitle.lower())
                oBP = BbcPage(about=sBbcTitle.lower())
                oBP.RelatedTaxon = oTaxon.about
                oBP.Url = sBbcUrl
                oBP.save()
    


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
    nsRoot = Namespace(username)
    
    sUserNS = nsRoot.path     
    sNcbiNS = sUserNS + u'/taxonomy/ncbi' # Ugly use of globals, I know. :-)
    
    ###################################
    # Define FOM-Object classes as a
    # more readable way to access tag-values
    # Defined here, since they depends on sNcbiNS being defined!
    ##
    # Ncbi-Taxon
    class NcbiTaxon(Object):
        TaxId = tag_value(sNcbiNS + u'/TaxId')
        ScientificName = tag_value(sNcbiNS + u'/ScientificName')
    # Wikipedia-Page
    class WikipediaPage(Object):
        RelatedTaxon = tag_value(sNcbiNS + u'/LinkOut/related-NcbiTaxon')
        PageId = tag_value(sUserNS + u'/wikipedia/pageid')
    # BBC-Page
    class BbcPage(Object):
        RelatedTaxon = tag_value(sNcbiNS + u'/LinkOut/related-NcbiTaxon')
        Url = tag_value(sUserNS + u'/bbcwildlife/url')
    ##
    # LinkOut-Provider
    class LinkOutProvider(Object):
        Id = tag_value(sNcbiNS + u'/LinkOut/Provider/Id')
        Name = tag_value(sNcbiNS + u'/LinkOut/Provider/Name')
        NameAbbr = tag_value(sNcbiNS + u'/LinkOut/Provider/NameAbbr')
        Url = tag_value(sNcbiNS + u'/LinkOut/Provider/Url')
    
    ##########################################
    # Query NCBI-Taxonomy objects in FluidInfo

    oTaxa = NcbiTaxon.filter(u'has '+ NcbiTaxon.__dict__['TaxId'].tagpath)
    
    print "Found", len(oTaxa), "objects with a", NcbiTaxon.__dict__['TaxId'].tagpath, "tag:"
    for oTaxon in oTaxa:
        print "Taxon:", oTaxon.about
        # Get LinkOut items. WARNING: Currently limited to iPhylo provider, for testing purposes.
        elObjUrl = GetLinkOutData(oTaxon.TaxId).findall('ObjUrl')
        print oTaxon.TaxId, "has", len(elObjUrl), "LinkOut entries."
        
        HandleIPhyloLinks(oTaxon, elObjUrl)
        

        
#        for eObjUrl in elObjUrl:
#            
#            ##########################################
#            # Create FluidInfoObject for the provider
#            # using full provider name as about tag value
#            oProv = LinkOutProvider(about=eObjUrl.find('Provider/Name').text.lower())
#            oProv.Id = int(eObjUrl.find('Provider/Id').text)
#            oProv.Name = unicode(eObjUrl.find('Provider/Name').text)
#            oProv.NameAbbr = unicode(eObjUrl.find('Provider/NameAbbr').text)
#            oProv.Url = unicode(eObjUrl.find('Provider/Url').text)
#            oProv.save()
#            print "Created/updated LinkOut provider data on about:",oProv.about," with uid:", oProv.uid
#            
#    # Put some usefull info on the description-tag of the namespace objects.
#    Namespace(sUserNS+u'/taxonomy/ncbi/LinkOut')._set_description( u'NCBI LinkOut data.')
#    Namespace(sUserNS+u'/taxonomy/ncbi/LinkOut/Provider')._set_description( u'LinkOut Provider data')
    
    
    
    

