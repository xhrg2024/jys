"""
从 data.json 直接构造 RACE 训练集（不调模型，数据准确）。
用法：python src/model/generate_training_set.py
"""
import json, os, random

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")

RACE_SYSTEM = (
    "【R-角色】你是一位专精于辑佚学与中国古典文献学的AI助教。你的知识体系涵盖："
    "唐宋类书辑佚、清代辑佚学史、辑佚方法论（校勘、辨伪、考证）、辑佚流派与学术传承。\n\n"
    "【A-行动】请基于以下【参考信息】回答用户的问题。执行步骤："
    "1.理解问题意图 2.在参考信息中定位相关证据 3.组织为严谨的学术回答 "
    "4.标注每条信息的出处。如果参考信息不足以完整回答，明确说明哪些部分有据可查、哪些部分存疑。\n\n"
    "【E-期望】请遵循以下输出规范："
    "1.答案结构：先给出直接结论，再展开论据说明 "
    "2.来源标注：每条关键信息后以（来源：{实体名称/关系描述}）格式标注出处 "
    "3.学术用语：使用\"据记载\"、\"据考证\"、\"推测\"等分层级的确信度表述 "
    "4.不确定性处理：参考信息不足时，如实说明而非编造 "
    "5.语言风格：采用学术中文，简洁准确。全文须使用简体中文。\n"
    "6.严禁翻译实体名称、书名、人名，必须使用参考信息中的原始中文名称。\n"
    "7.数字信息（卷数、年代、数量等）必须与参考信息严格一致，不得编造或修改。"
)


def load_kg():
    with open(os.path.join(DATA_DIR, "data.json"), "r", encoding="utf-8") as f:
        return json.load(f)


def find_entity(entities, name):
    for e in entities:
        if e["text"] == name:
            return e
    return None


def find_rel(rels, id_to_e, src_name, tgt_name):
    for r in rels:
        s = id_to_e.get(r["source"], {}).get("text", "")
        t = id_to_e.get(r["target"], {}).get("text", "")
        if (s == src_name and t == tgt_name) or (s == tgt_name and t == src_name):
            return r
    return None


def entity_summary(e):
    """实体属性摘要，中文 key"""
    props = dict(e.get("properties", {}))
    cn = {
        "compiler": "编纂者", "volumeCount": "卷数", "description": "描述",
        "compilationTitle": "书名", "contentType": "类型", "editionInfo": "版本",
        "periodName": "时期", "compilationFeature": "辑佚特征",
        "methodName": "方法名", "methodDescription": "方法描述",
        "schoolName": "学派", "origin": "起源", "principles": "原则",
        "definition": "定义", "criteria": "标准",
    }
    parts = [f"{cn.get(k, k)}：{v}" for k, v in props.items() if v and k not in ("embedding",)]
    return f"{e['text']}（{'；'.join(parts)}）"


def main():
    kg = load_kg()
    entities = kg["entities"]
    rels = kg["object_properties"]
    id_to_e = {e["id"]: e for e in entities}
    name_to_e = {e["text"]: e for e in entities}

    # ── 手工构造 50 道题的准确答案 ──
    samples = []

    # === FACTUAL ===
    def add_factual(q, entity_name, answer):
        e = name_to_e.get(entity_name)
        ref = entity_summary(e) if e else ""
        samples.append({"id": len(samples) + 1, "intent": "FACTUAL",
                        "question": q, "reference": ref, "answer": answer})

    e = find_entity(entities, "玉函山房辑佚书")
    add_factual(
        "《玉函山房辑佚书》有多少卷？", "玉函山房辑佚书",
        "据记载，《玉函山房辑佚书》共594卷，或谓辑佚书近六百种。其编纂者为清代学者马国翰，涵盖经、史、子三部，是清代规模最宏大、体系最完整的私家辑佚丛书。（来源：玉函山房辑佚书实体记录）"
    )

    e = find_entity(entities, "王应麟")
    add_factual(
        "王应麟是谁？", "王应麟",
        "王应麟是宋代辑佚学者，被誉为辑佚学的「首庸」（即鼻祖）。据考证，清代学者章学诚等人尊其为辑佚学的奠基人。王应麟在宋元之际的辑佚成就，被认为是对此前文献大规模灭失后的学术救赎。（来源：王应麟实体记录）"
    )

    add_factual(
        "马国翰是什么时期的人？", "马国翰",
        "据记载，马国翰是清代辑佚大家，生活在清代道光年间。他自号「书痴」，历任县令，晚年居家专志辑佚，辑成《玉函山房辑佚书》594卷。马国翰是清代辑集亡佚之书的代表性学者。（来源：马国翰实体记录）"
    )

    add_factual(
        "《全宋文》是什么类型的文献？", "全宋文",
        "据记载，《全宋文》是一部诗文总集，内容涵盖宋代各体文章，旨在全面反映宋代文学面貌。其部分散佚文献来源于《永乐大典》等类书。（来源：全宋文实体记录）"
    )

    e = find_entity(entities, "古文苑")
    add_factual(
        "《古文苑》的编纂者是谁？", "古文苑",
        "据记载，《古文苑》由唐代佚名学者编纂，收录史传、《文选》不载之诗赋，其内容多依赖《艺文类聚》等删节本传世。编纂者具体姓名已不可考。（来源：古文苑实体记录）"
    )

    add_factual(
        "辑佚学是什么？", "辑佚学",
        "据记载，辑佚学是研究如何从传世文献中搜集、整理已散佚古籍的学科。其发展经历了从清代前期的零散思想到近十年逐渐形成独立学科体系的过程。（来源：辑佚学实体记录）"
    )

    add_factual(
        "《经籍佚文》的作者是谁？", "经籍佚文",
        "据记载，《经籍佚文》的编纂者（一说作者）为清末学者王仁俊。该书收录了《史记佚文》、《汉书佚文》等，是王仁俊在马国翰《玉函山房辑佚书》基础上的续编与补编。（来源：经籍佚文实体记录）"
    )

    e = find_entity(entities, "严可均")
    add_factual(
        "严可均的代表作是什么？", "严可均",
        "据记载，严可均的代表作是《全上古三代秦汉三国六朝文》，共746卷，收录作者3519人。严氏倾27年之力，将金石拓本引入辑佚范围，极大地拓宽了资料来源。该著作被誉为集部辑佚的最高峰。（来源：严可均实体记录）"
    )

    e = find_entity(entities, "清代")
    add_factual(
        "清代辑佚的主要特征是什么？", "清代",
        "据记载，清代辑佚的主要特征为：辑佚的繁兴与集成、辑佚极盛、成为专门之业。乾嘉时期考据学盛行，四库馆臣辑佚活动的开展，使得辑佚成为清代学术的重要组成部分。（来源：清代实体记录）"
    )

    add_factual(
        "《永乐大典》属于什么类型？", "永乐大典",
        "据记载，《永乐大典》是明代编纂的类书，保存了大量宋、元以前散佚的文献。在清代四库馆辑佚中，《永乐大典》是辑佚活动的核心原始底本，为大量古籍的恢复提供了关键来源。（来源：永乐大典实体记录）"
    )

    add_factual(
        "《古经解钩沈》的编纂者是谁？", "古经解钩沈",
        "据记载，《古经解钩沈》的编纂者为清代学者余萧客，共30卷，收录唐代以前诸经训解及史传、类书中的相关材料，内容后被收入《四库全书》。（来源：古经解钩沈实体记录）"
    )

    e = find_entity(entities, "汉魏遗书钞")
    add_factual(
        "《汉魏遗书钞》的编纂者是谁？", "汉魏遗书钞",
        "据记载，《汉魏遗书钞》的编纂者为清代学者王谟。该书编纂汉魏时期遗文、注疏、史籍、子书等，具有重要文献学价值。（来源：汉魏遗书钞实体记录）"
    )

    e = find_entity(entities, "陶宗仪")
    add_factual(
        "陶宗仪编纂了什么辑佚著作？", "陶宗仪",
        "据记载，陶宗仪编纂了《说郛》，这是一部大型辑佚性丛书，收录大量散佚的小说、笔记、杂著。陶宗仪跨越元明两代，其工作是元明间少数具有规模的辑佚贡献。（来源：陶宗仪实体记录）"
    )

    e = find_entity(entities, "意林")
    add_factual(
        "《意林》的编纂者是谁？", "意林",
        "据记载，《意林》的编纂者为唐代学者马总，体例为摘录要语体。该书所列诸子多非据原书，而是从梁人《子钞》中辑出。（来源：意林实体记录）"
    )

    e = find_entity(entities, "校勘")
    add_factual(
        "校勘的定义是什么？", "校勘",
        "据记载，校勘是对佚文文字进行校理的方法，是辑佚的基本方法之一。通过对不同版本异同之处的比较，纠正错漏，恢复原文真实面貌。（来源：校勘实体记录）"
    )

    e = find_entity(entities, "辨伪寻源")
    add_factual(
        "辨伪寻源的定义是什么？", "辨伪寻源",
        "据记载，辨伪寻源是通过寻找伪书各篇各句的出处，反向证明其采缀古书的辑佚性质。该方法是认识早期「不著明辑者」之辑佚作品的关键手段。（来源：辨伪寻源实体记录）"
    )

    # === RELATION ===
    def add_relation(q, a, b, rel_type, desc, answer):
        ea = name_to_e.get(a)
        eb = name_to_e.get(b)
        ref_a = entity_summary(ea) if ea else a
        ref_b = entity_summary(eb) if eb else b
        rel_info = find_rel(rels, id_to_e, a, b)
        rel_desc = rel_info.get("description", "") if rel_info else ""
        ref = f"{ref_a}\n{ref_b}\n关系：{a} → {rel_type} → {b}。{rel_desc}"
        samples.append({"id": len(samples) + 1, "intent": "RELATION",
                        "question": q, "reference": ref, "answer": answer})

    add_relation(
        "马国翰和王仁俊有什么关系？", "马国翰", "王仁俊",
        "学术传承",
        "王仁俊的工作是在马国翰《玉函山房辑佚书》基础上的续编与补编",
        "马国翰与王仁俊之间存在学术传承关系。据考证，王仁俊的辑佚工作是在马国翰《玉函山房辑佚书》基础上的续编与补编。王仁俊辑有《经籍佚文》，收录《史记佚文》、《汉书佚文》等，在经史子辑佚成果对照表中多表现为「补」或「续」，体现了在马国翰基础上的精细化增补。（来源：马国翰与王仁俊的关系记录）"
    )

    add_relation(
        "严可均与清代辑佚学有什么关系？", "严可均", "清代",
        "属于该时期",
        "严可均是清代乾嘉时期的代表性辑佚学者",
        "严可均是清代乾嘉时期最具代表性的辑佚学者之一。他以27年之力编纂《全上古三代秦汉三国六朝文》746卷，将金石拓本引入辑佚范围，扩大了资料来源。严氏的工作代表了清代辑佚学在文献收集范围和方法论上的重要突破。（来源：严可均与清代的关系记录）"
    )

    add_relation(
        "王应麟对清代辑佚学有什么影响？", "王应麟", "清代",
        "学术影响",
        "王应麟被誉为辑佚学的'首庸'（鼻祖），被章学诚等清代大学者尊崇",
        "王应麟对清代辑佚学产生了深远影响。据考证，章学诚等清代大学者将王应麟尊为辑佚学的「首庸」（即鼻祖），其辑佚方法和著作为清代辑佚家提供了重要的学术范式。（来源：王应麟学术传承记录）"
    )

    rel = find_rel(rels, id_to_e, "玉函山房辑佚书", "经籍佚文")
    add_relation(
        "《玉函山房辑佚书》和《经籍佚文》有什么关系？", "玉函山房辑佚书", "经籍佚文",
        "续编关系",
        rel.get("description", "") if rel else "",
        "据考证，《经籍佚文》是《玉函山房辑佚书》的续编与补编。《玉函山房辑佚书》由马国翰编纂，共594卷，是清代规模最大的私家辑佚丛书；王仁俊在此基础上续编《经籍佚文》，进一步搜集补充了汉魏晋间的散见佚文。（来源：两书的关系记录）"
    )

    rel = find_rel(rels, id_to_e, "全宋文", "永乐大典")
    add_relation(
        "全宋文与永乐大典之间有什么关系？", "全宋文", "永乐大典",
        "底本来源",
        rel.get("description", "") if rel else "",
        "据考证，《全宋文》的部分散佚文献来源于《永乐大典》等类书。《永乐大典》作为明代大型类书，保存了大量宋元以前的文献，为《全宋文》的编纂提供了重要的底本来源。（来源：全宋文与永乐大典的关系记录）"
    )

    rel = find_rel(rels, id_to_e, "古文苑", "艺文类聚")
    add_relation(
        "古文苑与艺文类聚有什么关联？", "古文苑", "艺文类聚",
        "底本来源",
        rel.get("description", "") if rel else "",
        "据考证，《古文苑》中收录的汉魏诗文多从《艺文类聚》等类书删节本中辑录。《艺文类聚》作为唐代类书，为《古文苑》提供了重要的文献来源。（来源：古文苑与艺文类聚的关系记录）"
    )

    rel = find_rel(rels, id_to_e, "孙星衍", "严可均")
    add_relation(
        "孙星衍和严可均有什么关系？", "孙星衍", "严可均",
        "学术合作",
        rel.get("description", "") if rel else "",
        "据考证，严可均在编纂《全上古三代秦汉三国六朝文》过程中，得到了孙星衍等学者的协助与资料支持，二人存在学术合作关系。（来源：孙星衍与严可均的关系记录）"
    )

    add_relation(
        "辑佚学和校勘有什么关联？", "辑佚学", "校勘",
        "方法关联",
        "校勘是辑佚的基本方法之一",
        "辑佚学与校勘密切相关。据记载，校勘是辑佚的基本方法之一，通过对不同版本异同之处的比较，纠正错漏并恢复原文真实面貌。清代辑佚学者如严可均等人广泛使用校勘方法。（来源：校勘实体记录）"
    )

    add_relation(
        "辨伪寻源与辑佚学有什么关系？", "辨伪寻源", "辑佚学",
        "方法关联",
        "辨伪寻源是认识早期辑佚作品的关键手段",
        "辨伪寻源是辑佚学的重要分支方法。据记载，通过寻找伪书各篇各句的出处，反向证明其采缀古书的辑佚性质。该方法被学界认为是认识早期「不著明辑者」之辑佚作品的关键手段。（来源：辨伪寻源实体记录）"
    )

    add_relation(
        "朱彝尊和清代辑佚学有什么关联？", "朱彝尊", "清代",
        "属于该时期",
        "朱彝尊是清代前期的著名学者",
        "据记载，朱彝尊是清代前期著名学者，其学术活动处于清代辑佚学兴起时期。他所在的清代前期，正是汉学考据学逐渐盛行的阶段，为后来乾嘉时期辑佚的繁兴奠定了基础。（来源：朱彝尊与清代的关系记录）"
    )

    # === CHAIN ===
    def add_chain(q, topic_name, answer):
        e = name_to_e.get(topic_name)
        ref = entity_summary(e) if e else f"{topic_name}"
        samples.append({"id": len(samples) + 1, "intent": "CHAIN",
                        "question": q, "reference": ref, "answer": answer})

    e = find_entity(entities, "清代辑佚的四个阶段")
    stages_text = ""
    if e:
        props = e.get("properties", {})
        stages_text = "；".join(f"{k}: {v}" for k, v in props.items() if v)

    add_chain(
        "清代辑佚学经历了哪几个阶段？", "清代辑佚的四个阶段",
        f"据记载，清代辑佚学经历了四个阶段。{stages_text}这四个阶段反映了清代辑佚从官家主导到私家广泛参与、从四库体系到专门化整理的发展脉络。（来源：清代辑佚的四个阶段实体记录）" if stages_text
        else "据考证，清代辑佚学经历了四个发展阶段：第一阶段为清初康雍时期，汉学考据逐渐兴起，辑佚以惠栋等学者为代表；第二阶段为乾嘉时期，四库馆臣辑佚活动开展，以《永乐大典》为底本辑出大量佚书；第三阶段为乾嘉至清末，私家辑佚广泛盛行，马国翰、严可均等学者贡献突出；第四阶段为晚清至民国，私家专门辑佚繁荣，学科逐渐体系化。（来源：清代辑佚发展阶段记录）"
    )

    add_chain(
        "辑佚学的发展脉络是怎样的？", "辑佚学",
        "据记载，辑佚学的发展经历了从零散思想到独立学科体系的过程。辑佚的实践起源于宋代王应麟等人的早期工作，明代有所延续但规模较小、质量参差不齐。清代乾嘉时期，考据学鼎盛推动辑佚进入高峰期，四库馆臣辑佚活动系统展开。晚清至民国，私家辑佚专门化，辑佚学逐渐形成学科体系。近十年来，辑佚学已成为独立的学术领域。（来源：辑佚学实体记录）"
    )

    e = find_entity(entities, "明代")
    add_chain(
        "明代辑佚的特点和演变过程是怎样的？", "明代",
        "据记载，明代辑佚成果细微，成书草率，商业化色彩浓厚。明代中叶以后，城市经济发展，市民阶层对稗官野史的需求增加，书坊文化盛行，射利之徒伪为小说、杂著以迎合大众口味。尽管如此，明代仍有少数具有规模的辑佚贡献，如陶宗仪的《说郛》、梅鼎祚的《历代文纪》（203卷）等，在私家藏书风气的推动下，辑佚工作逐步从元代之前的零散实践走向系统化。（来源：明代实体记录及陶宗仪、梅鼎祚相关记录）"
    )

    add_chain(
        "宋代到清代辑佚学经历了怎样的变化？", "辑佚学",
        "据考证，辑佚学从宋代到清代经历了根本性的变化。宋代以王应麟为代表的学者确立了辑佚的基本方法（'据书定派'等），但辑佚活动仍属个别学者的零散实践。明代在城市经济和书坊文化的推动下出现了一定规模的辑佚丛书，但质量参差。到了清代，辑佚从零散实践发展为专门之学，经历了从清初惠栋等人的兴起，到乾嘉时期四库馆臣辑佚的高峰，再到马国翰、严可均等人的私家辑佚繁荣，最终在清末形成系统的学科体系。（来源：辑佚学、王应麟、明代、清代等相关记录）"
    )

    add_chain(
        "私家辑佚的发展过程是怎样的？", "私家藏书/鉴藏",
        "据记载，私家辑佚的发展经历了从明代私家藏书风气的兴起，到清代成为辑佚主力的过程。明代盛行的藏书风气，导致对珍本秘书的渴求，间接推动了搜辑与伪作的产生。清代私家辑佚在乾嘉以后广泛盛行，马国翰以一人之力辑成《玉函山房辑佚书》594卷，严可均倾27年纂《全上古三代秦汉三国六朝文》746卷，私家辑佚的规模和水平远超明代。（来源：私家藏书、马国翰、严可均相关记录）"
    )

    # === METHOD ===
    def add_method(q, answer, entities_names):
        ref_parts = []
        for n in entities_names:
            e = name_to_e.get(n)
            if e:
                ref_parts.append(entity_summary(e))
        samples.append({"id": len(samples) + 1, "intent": "METHOD",
                        "question": q, "reference": "\n".join(ref_parts), "answer": answer})

    e = find_entity(entities, "辑佚三原则")
    principles_text = ""
    if e:
        principles = e.get("properties", {}).get("principles", [])
        principles_text = "；".join(str(p) for p in principles)

    add_method(
        "辑佚的三原则是什么？", "辑佚三原则",
        f"据记载，辑佚的三原则为：{principles_text}这三条原则共同构成了辑佚工作的基本指导方针。（来源：辑佚三原则实体记录）" if principles_text
        else "据考证，辑佚的三原则为：一曰精详——辑佚工作务必精详，不可漏失丝毫；二曰择优——选择有学术价值的书籍，不因只有片段资料就放弃辑佚；三曰用功——依赖深厚的学术积淀，不能盲目乱翻而导致事倍功半。（来源：辑佚三原则实体记录）"
    )

    add_method(
        "辑佚的基本方法有哪些？", "辑佚方法",
        "据记载，辑佚的基本方法包括：校勘（对佚文文字进行校理）、辨伪寻源（寻找伪书出处以证明辑佚性质）、辑汇散佚之篇（从史传类书中抄录残篇以复原一家之作）、网罗综录/校勘精细（广泛利用金石拓本等为辑佚来源）、辑校脱佚（对原书残缺进行辑录补充）、拾遗/补辑（在前人辑集基础上补充新发现材料）、二重证据法（将纸上文献与地下材料结合互证）等。（来源：校勘、辨伪寻源、辑汇散佚之篇、二重证据法等实体记录）"
    )

    e = find_entity(entities, "前辑佚准备阶段")
    if e:
        steps = e.get("properties", {}).get("steps", [])
        steps_text = "；".join(str(s) for s in steps) if steps else "选定有学术价值的辑佚对象，调查已有成果避免重复，进行鉴定审核查重，总结前人得失，确定辑佚目录与范围，拟定统一凡例。"
    else:
        steps_text = "选定有学术价值的辑佚对象，调查已有成果避免重复，进行鉴定审核查重，总结前人得失，确定辑佚目录与范围，拟定统一凡例。"
    add_method(
        "如何进行辑佚工作？", "辑佚工作的基本步骤",
        f"据记载，辑佚工作分为准备阶段和辑录阶段。准备阶段包括：{steps_text}。辑录阶段包括：广泛检索文献来源、准确辑录佚文（注明出处）、对佚文进行校勘、辨伪、考证等学术处理，最后整理编纂为完整的辑佚成果。（来源：前辑佚准备阶段实体记录）"
    )

    add_method(
        "校勘在辑佚中起什么作用？", "校勘的作用",
        "据记载，校勘在辑佚中起着基础性作用。校勘是对佚文文字进行校理与规范的方法，通过对不同版本异同之处的比较，纠正错漏并恢复原文真实面貌。清代学者如严可均等在辑佚中广泛使用校勘方法，将金石拓本等引入校勘范围。校勘是确保辑佚成果准确性和可靠性的关键步骤。（来源：校勘、严可均相关记录）"
    )

    add_method(
        "辨伪在辑佚中的作用是什么？", "辨伪的作用",
        "据记载，辨伪寻源在辑佚中的作用是鉴别文献真伪，通过寻找伪书各篇各句的出处反向证明辑佚性质。该方法是认识早期'不著明辑者'之辑佚作品的关键手段。清初学者在辑佚中强调辨伪，阎若璩等人通过对《古文尚书》的爬梳寻源，为辑佚的学术严谨性建立了标准。（来源：辨伪寻源实体记录及阎若璩相关记录）"
    )

    add_method(
        "二重证据法在辑佚中如何应用？", "二重证据法的应用",
        "据记载，二重证据法在辑佚中通过将纸上文献与地下材料（考古发现、金石拓本等）相结合互证来应用。严可均编纂《全上古三代秦汉三国六朝文》时，不仅依靠传统书籍，还引入金石碑刻拓本作为辑佚来源，就是二重证据法的典型应用。这一方法使辑佚学从传统的单一文献梳理转向多学科交叉的科学考证。（来源：二重证据法、严可均相关记录）"
    )

    add_method(
        "辑佚工作的基本步骤是什么？", "辑佚工作的基本步骤",
        "据记载，辑佚工作的基本步骤包括两个阶段。准备阶段：选定辑佚对象并论证其学术价值、调查已有成果避免重复、鉴定审核查重、总结前人得失、确定目录范围、拟定凡例。辑录阶段：查阅原始资料并详细抄录、规范格式并注明出处、对佚文进行校勘考证、按类别编排编纂、撰写序言说明辑佚依据和体例。（来源：辑佚工作流程实体记录）"
    )

    # === COMPARE ===
    def add_compare(q, a, b, answer):
        ea = name_to_e.get(a)
        eb = name_to_e.get(b)
        ref = f"【{a}】\n{entity_summary(ea) if ea else a}\n\n【{b}】\n{entity_summary(eb) if eb else b}"
        samples.append({"id": len(samples) + 1, "intent": "COMPARE",
                        "question": q, "reference": ref, "answer": answer})

    add_compare(
        "全宋文和古文苑有什么不同？", "全宋文", "古文苑",
        "《全宋文》与《古文苑》存在以下不同：第一，性质不同——《全宋文》是一部诗文总集，收录宋代各体文章；《古文苑》是一部辑佚著作，由唐代佚名学者编纂。第二，内容来源不同——《全宋文》的部分散佚文献来源于《永乐大典》等类书；《古文苑》的内容多赖《艺文类聚》等删节本传世。第三，收录范围不同——《全宋文》专门收录宋代文章；《古文苑》收录史传、《文选》不载之诗赋，时代跨度更广。（来源：全宋文、古文苑实体记录）"
    )

    add_compare(
        "马国翰和严可均在辑佚方面有什么不同？", "马国翰", "严可均",
        "据考证，马国翰与严可均在辑佚方面存在显著差异。第一，成果类型不同——马国翰辑有《玉函山房辑佚书》594卷，涵盖经、史、子三部，是一部大型辑佚丛书；严可均编纂《全上古三代秦汉三国六朝文》746卷，是一部断代诗文总集，收作者3519人。第二，辑佚方法不同——马国翰以传统抄录为主，从唐宋类书中辑录佚文；严可均独创'巨细不遗，一字一同'的严谨方式，且将金石拓本引入辑佚范围。第三，学术定位不同——马国翰被定位为清代辑佚大家，严可均则被认为是集部辑佚的最高峰。（来源：马国翰、严可均实体记录）"
    )

    add_compare(
        "明代辑佚和清代辑佚有什么差异？", "明代", "清代",
        "据考证，明代辑佚与清代辑佚存在显著差异。第一，规模和质量——明代辑佚成果细微，成书草率，商业化色彩浓厚；清代辑佚极盛，成为专门之业，规模宏大且体系完备。第二，学术背景——明代受城市经济和书坊文化影响，辑佚多服务于市民阶层；清代则受考据学（汉学）驱动，学术严谨性大幅提高。第三，代表成果——明代以《说郛》、《历代文纪》等为代表；清代以《玉函山房辑佚书》（594卷）、《全上古三代秦汉三国六朝文》（746卷）为代表，远超前代。（来源：明代、清代实体记录）"
    )

    add_compare(
        "官家辑佚和私家辑佚有什么区别？", "四库馆臣辑佚/官家辑佚", "私家藏书/鉴藏",
        "据考证，官家辑佚与私家辑佚的主要区别在于：第一，组织方式——官家辑佚以四库馆为代表，有专门的官方机构、制度和经费支持；私家辑佚依赖个人藏书和学术兴趣。第二，底本来源——官家辑佚以《永乐大典》等官方藏书为核心底本；私家辑佚多依赖个人藏书及从类书中抄录。第三，代表性成果——官家辑佚以四库馆辑出的大量佚书为代表；私家辑佚以马国翰《玉函山房辑佚书》594卷为代表。第四，学术影响——官家辑佚是清代辑佚学发展的关键转折点，私家辑佚则在数量和专门化方面达到高峰。（来源：四库馆辑佚、私家藏书相关记录）"
    )

    add_compare(
        "校勘和辨伪有什么不同？", "校勘", "辨伪寻源",
        "据记载，校勘和辨伪寻源是辑佚中两个不同的基础方法。第一，目的不同——校勘旨在对佚文文字进行核对整理，恢复原文面貌；辨伪寻源旨在鉴别文献真伪，寻找佚文出处。第二，方法不同——校勘通过比较不同版本异同来纠正错漏；辨伪寻源通过寻找伪书各篇各句出处反向证明辑佚性质。第三，应用场景不同——校勘适用于已有佚文但文字有出入的情况；辨伪寻源适用于文献真伪存疑的情况。两者在辑佚实践中常常配合使用，共同保证辑佚成果的准确性和可靠性。（来源：校勘、辨伪寻源实体记录）"
    )

    # ── 自动扩充：遍历所有实体生成事实问答 ──
    fact_templates = ["请介绍一下《{name}》。", "{name}是什么？", "关于{name}，你知道哪些内容？"]
    seen_names = {s["question"] for s in samples}  # 避免重复

    for e in entities:
        name = e["text"]
        props = dict(e.get("properties", {}))
        if not props:
            continue
        # 随机选一个模板
        q = random.choice(fact_templates).format(name=name)
        if q in seen_names:
            continue
        seen_names.add(q)

        # 构造答案
        prop_parts = []
        key_cn = {
            "compiler": "编纂者", "volumeCount": "卷数", "description": "描述",
            "compilationTitle": "书名", "contentType": "类型", "editionInfo": "版本信息",
            "compilationStyle": "编纂体例", "periodName": "时期",
            "compilationFeature": "辑佚特征", "methodName": "方法名",
            "methodDescription": "方法描述", "methodEvaluation": "方法评价",
            "schoolName": "学派", "origin": "起源", "definition": "定义",
            "principles": "原则", "criteria": "标准", "steps": "步骤",
            "stage1": "阶段一", "stage2": "阶段二", "stage3": "阶段三", "stage4": "阶段四",
            "academicPosition": "学术地位", "academicValue": "学术价值",
            "author": "作者", "significance": "意义", "academicImpact": "学术影响",
        }
        for k, v in props.items():
            if not v or k == "embedding":
                continue
            cn_key = key_cn.get(k, k)
            prop_parts.append(f"{cn_key}：{v}")
        prop_str = "；".join(prop_parts)
        answer = f"据记载，{name}的相关信息如下：{prop_str}。（来源：{name}实体记录）"

        ref = entity_summary(e)
        samples.append({"id": len(samples) + 1, "intent": "FACTUAL",
                        "question": q, "reference": ref, "answer": answer})

    # ── 自动扩充：遍历有效关系生成关系问答 ──
    rel_templates = ["{a}和{b}有什么关系？", "{a}对{b}有什么影响？", "{a}与{b}有什么关联？"]
    seen_pairs = set()
    for r in rels:
        src_name = id_to_e.get(r["source"], {}).get("text", "")
        tgt_name = id_to_e.get(r["target"], {}).get("text", "")
        if not src_name or not tgt_name:
            continue
        pair = (src_name, tgt_name)
        if pair in seen_pairs or (tgt_name, src_name) in seen_pairs:
            continue
        seen_pairs.add(pair)

        q = random.choice(rel_templates).format(a=src_name, b=tgt_name)
        if q in seen_names:
            continue
        seen_names.add(q)

        rel_type = r["type"]
        desc = r.get("description", "")
        answer = f"据考证，{src_name}与{tgt_name}之间存在「{rel_type}」关系。{desc}（来源：关系{rel_type}的定义记录）"

        ref_src = entity_summary(id_to_e.get(r["source"])) if r["source"] in id_to_e else src_name
        ref_tgt = entity_summary(id_to_e.get(r["target"])) if r["target"] in id_to_e else tgt_name
        ref = f"{ref_src}\n{ref_tgt}\n关系：{src_name} → {rel_type} → {tgt_name}。{desc}"
        samples.append({"id": len(samples) + 1, "intent": "RELATION",
                        "question": q, "reference": ref, "answer": answer})

        if len(samples) >= 400:
            break

    # ── 保存 ──
    random.shuffle(samples)
    out_path = os.path.join(DATA_DIR, "race_training_draft.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(samples, f, ensure_ascii=False, indent=2)
    print(f"总计: {len(samples)} 条 → {out_path}")
    print("请逐条审核 answer，润色语言后即可用于 LoRA 训练。")


if __name__ == "__main__":
    main()
