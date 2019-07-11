import sys
import os
import re
import json
from cuda_fmt import get_config_filename

sys.path.append(os.path.dirname(__file__))
import uroborosqlfmt
from uroborosqlfmt.config import LocalConfig
from uroborosqlfmt.commentsyntax import Doma2CommentSyntax

def get_ops():
    fn = get_config_filename('SQL Uroboro Format')
    if os.path.isfile(fn):
        s = open(fn, 'r').read()
        #del // comments
        s = re.sub(r'(^|[^:])//.*'  , r'\1', s)
        d = json.loads(s)
    else:
        d = {}

    config = LocalConfig()
    config.set_case(d.get("uf_case", "upper"))
    config.set_reserved_case(d.get("uf_reserved_case", "upper"))
    config.set_input_reserved_words(d.get("uf_reserved_words", config.input_reserved_words))
    uroborosqlfmt.config.glb.escape_sequence_u005c = d.get("uf_escapesequence_u005c", False)
    if d.get("uf_comment_syntax", "uroboroSQL").upper() == "DOMA2":
        config.set_commentsyntax(Doma2CommentSyntax())

    tab_config = {}
    tab_config["size"] = d.get("uf_tab_size", 4)
    tab_config["spaces"] = d.get("uf_translate_tabs_to_spaces", True)

    return config, tab_config


def do_format(text):
    op, op_tab = get_ops()
    text = uroborosqlfmt.format_sql(text, op)
    if op_tab["spaces"]:
        text = text.replace('\t', ' ' * op_tab["size"])
    return text
