#%%
from genesis.models import SpeedProfile
import pandas as pd

#%%
sp = SpeedProfile()
print(len(sp.get))
# %%
sp.get
# %%
sp.save(base_path='tests/data/')
# %%
sp.test()
# %%

