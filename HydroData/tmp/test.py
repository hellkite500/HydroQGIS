#/usr/bin/env python
import pandas as pd
import skew_map
df = pd.read_msgpack('peak_data.msg')

#TODO/FIXME should be a better way than looking up EACH record!!!
df['skew'] = df.apply(skew_map.getSkew, axis=1)

groups = df.groupby(level='site_no')

for site, data in groups:
    print site
    print data.ix[site]
    


#save this dataframe to a light binary format. This also perserves the multi-index hiearchy.
#TODO This might be a good place to look up and add generalized skew values to this data frame.

df.to_msgpack('skew_added.msg')
