fiTaxonomy
==========
Tools to populate FluidInfo with taxonomy data.


A testbench for @axeloide's thoughts about leveraging FluidInfo to get difficult data into a more usable representation.



PopulateTaxa.py
---------------
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

Currently it processes all the species of division primates, without digits in their scientific names.


PopulateLinkOut.py
------------------
Iterates over all FluidInfo objects with a ./taxonomy/ncbi/TaxId tag and
uses the NCBI E-Utility Elink to recreate a web of references to related
objects/datasources in FluidInfo, creating and populating those where necessary.

http://www.ncbi.nlm.nih.gov/books/NBK25499/#chapter4.ELink



ToDo
----
* Improve efficiency:
    + Query Efetch in batches, instead of one-by-one
    + Tag FluidInfo objects in a single call. Refer to: https://gist.github.com/1431251
    
* Error checking, error checking, error checking!
  Everything is currently coded in a "blindly optimistic" way.
  
* Include a timestamp tag like "./taxonomy/ncbi/timestamp-lastupdate"


Ideas for future tools
----------------------
* Create objects with about names that are:
    +   NCBI synonyms
    +   genebank common names
    *   etc...
  and tag them with something like "axeloide/taxonomy/redirect-to" 
  We can even be very creative and harvest other language's common names via Wikipedia.
  
  
  
 
 
   
 


Pointers to stuff
-----------------

Terry's hint about how to tag several tags at once:
https://gist.github.com/1431251


There seems to exist a tool that returns JSON formatted results, but it requires
an API key that must be requested, as documented here:
   http://entrezajax.appspot.com/developer.html
   
The corresponding uri would be:
http://entrezajax.appspot.com/elink?dbfrom=taxonomy&id=9482&cmd=llinks&apikey=<A registered API key>


