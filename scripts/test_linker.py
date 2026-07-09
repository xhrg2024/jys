"""测试 EntityLinker 是否能正常加载 entity_dict.json"""
import sys
sys.path.insert(0, 'src')
from perception.entity_linker import EntityLinker

linker = EntityLinker()
print(f"实体链接器加载成功，共 {len(linker.entities)} 个实体")
hits = linker.link('王应麟')
print(f"\"王应麟\" 匹配结果: {hits}")