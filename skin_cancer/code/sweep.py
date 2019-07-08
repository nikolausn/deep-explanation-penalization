import itertools
from slurmpy import Slurm
import os
#partition = 'low'

# sweep different ways to initialize weights= 
params_to_vary = {
    'regularizer_rate':   [0, 10,  ]    ,
     'seed':   [42,   ]    ,
     'lr':   [0.01, 0.1,  ]    ,
      'momentum':   [0.5, 0.9, ]    ,
     
     'batch_size':   [16, 32, ]    ,
}

ks = sorted(params_to_vary.keys())
vals = [params_to_vary[k] for k in ks]
param_combinations = list(itertools.product(*vals)) # list of tuples
print(param_combinations)
#for param_delete in params_to_delete:
#    param_combinations.remove(param_delete)

# iterate
import os

for i in range(len(param_combinations)):
    param_str = 'python finetune_features.py '
    for j, key in enumerate(ks):
        param_str += '--'+key + ' ' + str(param_combinations[i][j]) + ' '
    #s.run(param_str)
    print(param_str)
    os.system(param_str)
    