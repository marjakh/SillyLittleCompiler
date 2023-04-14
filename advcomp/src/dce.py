from cfg import CFGCreator

import sys

class DeadCodeEliminator:
  @staticmethod
  def eliminate(cfg):
    return cfg

if __name__ == '__main__':
  cfgs = CFGCreator.process(sys.stdin.read())
  new_cfgs = []
  for cfg in cfgs:
    new_cfg = DeadCodeEliminator.eliminate(cfg)
    new_cfgs.append(cfg)
  print(CFGCreator.reconstructJSON(cfgs))
