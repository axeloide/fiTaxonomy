fiTaxonomy
==========
Tools to populate FluidInfo with taxonomy data.


PopulateTaxa.py
---------------
Iterates over the taxa listed in the NCBI Taxonomy database and creates
corresponding FluidInfo objects with the most relevant tags.

Currently the list of imported taxa is limited to just a few, for testing purposes.
     TaxId: 9913  as about: bos taurus    with uid: 82b383ce-e42e-4d79-be6d-10d5283c5443
     TaxId: 9606  as about: homo sapiens  with uid: a1d5b1d2-8eef-450c-b772-b8e28ab58184


Other scripts will later iterate over those FluidInfo objects to perform other tasks.




Pointers to stuff
-----------------
There seems to exist a tool that returns JSON formatted results, but it requires
an API key that must be requested, as documented here:
   http://entrezajax.appspot.com/developer.html
   
The corresponding uri would be:
http://entrezajax.appspot.com/elink?dbfrom=taxonomy&id=9482&cmd=llinks&apikey=<A registered API key>


