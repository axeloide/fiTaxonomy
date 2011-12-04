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
    
    #################################
    # Define a FOM-Object class as a
    # more readable way to access our
    # Ncbi-Taxonomy objects
    # Defined here, since it depends on sNcbiNS being defined!
    class NcbiTaxon(Object):
        TaxId = tag_value(sNcbiNS + u'/TaxId')
        ScientificName = tag_value(sNcbiNS + u'/ScientificName')
    
    ##########################################
    # Query NCBI-Taxonomy objects in FluidInfo


    oTaxa = NcbiTaxon.filter(u'has '+ NcbiTaxon.__dict__['TaxId'].tagpath)
    
    print "Found", len(oTaxa), "objects with a", NcbiTaxon.__dict__['TaxId'].tagpath, "tag:"
    for oTaxon in oTaxa:
        print oTaxon.TaxId

