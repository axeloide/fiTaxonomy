fiTaxonomy
==========
Tools to populate FluidInfo with taxonomy data.


A testbench for @axeloide's thoughts about leveraging FluidInfo to get difficult data into a more usable representation.



PopulateTaxa.py
---------------
Iterates over the taxa listed in the NCBI Taxonomy database and creates
corresponding FluidInfo objects with the most relevant tags.

Uses the NCBI E-Utilities Esearch and Efetch:
* http://www.ncbi.nlm.nih.gov/books/NBK25499/#chapter4.ESearch
* http://www.ncbi.nlm.nih.gov/books/NBK25499/#chapter4.EFetch

This is kind of the core tool, since other scripts will later iterate over
those FluidInfo objects to perform other tasks.

For testing purposes, the list of imported taxa was first limited to just a few:
* TaxId: 9913  as about: bos taurus    with uid: 82b383ce-e42e-4d79-be6d-10d5283c5443
* TaxId: 9606  as about: homo sapiens  with uid: a1d5b1d2-8eef-450c-b772-b8e28ab58184

Currently it processes all the species of division primates, without digits in their scientific names.


PopulateLinkOut.py
------------------
Iterates over all FluidInfo objects with a ./taxonomy/ncbi/TaxId tag and
uses the NCBI E-Utility Elink to recreate a web of references to related
objects/datasources in FluidInfo, creating and populating those where necessary.

http://www.ncbi.nlm.nih.gov/books/NBK25499/#chapter4.ELink



ToDo
----    
* Error checking, error checking, error checking!
  Everything is currently coded in a "blindly optimistic" way.
  A HowTo on error checking urllib2 calls:
    + http://docs.python.org/howto/urllib2.html
  
* Include a timestamp tag like "./taxonomy/ncbi/timestamp-lastupdate"


Ideas for future tools
----------------------
* Create objects with about names that are:
    +   NCBI synonyms
    +   genebank common names
    *   etc...
  and tag them with something like "axeloide/taxonomy/redirect-to" 
  We can even be very creative and harvest other language's common names via Wikipedia.
  
  
* Create objects with about names that are:
   + Names of taxons in other languages. e.g. "perro", "dog", "hund"
   
  ... and then tag those with a "related-taxonomy" that links those to the
  actual taxonomy object. e.g. about="canis lupus"
  
  Use Wikipedia API to get foreign articles:
   + http://www.mediawiki.org/wiki/API:Query_-_Properties#langlinks_.2F_ll
     Examples:
        For a given article, get alternative languages:
        http://en.wikipedia.org/w/api.php?action=query&titles=Dog&prop=langlinks&lllimit=200&format=xml
        
        Get a list of all language-ids and autoglossonyms:
        http://en.wikipedia.org/w/api.php?action=query&meta=siteinfo&siprop=languages
        
        Or use a list by a more competent authority:
        http://www.sil.org/iso639-3/codes.asp
        
        http://www.loc.gov/standards/iso639-2/php/English_list.php
        http://www.loc.gov/standards/iso639-2/ISO-639-2_utf-8.txt
        
        http://www.loc.gov/standards/iso639-5/iso639-5.pipe.txt
        http://www.loc.gov/standards/iso639-5/iso639-5.skos.rdf
        
   
   
   
  
  
 
 
   
 


Pointers to stuff
-----------------

There seems to exist a tool that returns JSON formatted results, but it requires
an API key that must be requested, as documented here:
   http://entrezajax.appspot.com/developer.html
   
The corresponding uri would be:
http://entrezajax.appspot.com/elink?dbfrom=taxonomy&id=9482&cmd=llinks&apikey=<A registered API key>


