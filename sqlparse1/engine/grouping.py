# -*- coding: utf-8 -*-

import itertools

from sqlparse1 import sql
from sqlparse1 import tokens as T
import sys

try:
    next
except NameError:  # Python < 2.6
    next = lambda i: i.__next__()


def _group_left_right(tlist, ttype, value, cls,
                      check_right=lambda t: True,
                      check_left=lambda t: True,
                      include_semicolon=False):
    [_group_left_right(sgroup, ttype, value, cls, check_right, check_left,
                       include_semicolon) for sgroup in tlist.get_sublists()
     if not isinstance(sgroup, cls)]
    idx = 0
    token = tlist.token_next_match(idx, ttype, value)
    while token:
        right = tlist.token_next(tlist.token_index(token))
        left = tlist.token_prev(tlist.token_index(token))
        if right is None or not check_right(right):
            token = tlist.token_next_match(tlist.token_index(token) + 1,
                                           ttype, value)
        elif left is None or not check_left(left):
            token = tlist.token_next_match(tlist.token_index(token) + 1,
                                           ttype, value)
        else:
            if include_semicolon:
                sright = tlist.token_next_match(tlist.token_index(right),
                                                T.Punctuation, ';')
                if sright is not None:
                    # only overwrite "right" if a semicolon is actually
                    # present.
                    right = sright
            tokens = tlist.tokens_between(left, right)[1:]
            if not isinstance(left, cls):
                new = cls([left])
                new_idx = tlist.token_index(left)
                tlist.tokens.remove(left)
                tlist.tokens.insert(new_idx, new)
                left = new
            left.tokens.extend(tokens)
            for t in tokens:
                tlist.tokens.remove(t)
            token = tlist.token_next_match(tlist.token_index(left) + 1,
                                           ttype, value)


def _find_matching(idx, tlist, start_ttype, start_value, end_ttype, end_value):
    depth = 1
    for tok in tlist.tokens[idx:]:
        if tok.match(start_ttype, start_value):
            depth += 1
        elif tok.match(end_ttype, end_value):
            depth -= 1
            if depth == 1:
                return tok
    return None


def _group_matching(tlist, start_ttype, start_value, end_ttype, end_value,
                    cls, include_semicolon=False, recurse=False):

    #bugfix recurse
    # [_group_matching(sgroup, start_ttype, start_value, end_ttype, end_value,
    #                  cls, include_semicolon) for sgroup in tlist.get_sublists()
    [_group_matching(sgroup, start_ttype, start_value, end_ttype, end_value,
                     cls, include_semicolon, recurse) for sgroup in tlist.get_sublists()
     if recurse]
    if isinstance(tlist, cls):
        idx = 1
    else:
        idx = 0
    token = tlist.token_next_match(idx, start_ttype, start_value)
    while token:
        tidx = tlist.token_index(token)
        end = _find_matching(tidx, tlist, start_ttype, start_value,
                             end_ttype, end_value)
        if end is None:
            idx = tidx + 1
        else:
            if include_semicolon:
                next_ = tlist.token_next(tlist.token_index(end))
                if next_ and next_.match(T.Punctuation, ';'):
                    end = next_
            group = tlist.group_tokens(cls, tlist.tokens_between(token, end))
            _group_matching(group, start_ttype, start_value,
                            end_ttype, end_value, cls, include_semicolon)
            idx = tlist.token_index(group) + 1
        token = tlist.token_next_match(idx, start_ttype, start_value)


def group_if(tlist):
    _group_matching(tlist, T.Keyword, 'IF', T.Keyword, 'END IF', sql.If, True)


def group_for(tlist):
    _group_matching(tlist, T.Keyword, 'FOR', T.Keyword, 'END LOOP',
                    sql.For, True)


def group_foreach(tlist):
    _group_matching(tlist, T.Keyword, 'FOREACH', T.Keyword, 'END LOOP',
                    sql.For, True)


def group_begin(tlist):
    _group_matching(tlist, T.Keyword, 'BEGIN', T.Keyword, 'END',
                    sql.Begin, True)


def group_as(tlist):

    def _right_valid(token):
        # Currently limited to DML/DDL. Maybe additional more non SQL reserved
        # keywords should appear here (see issue8).
        return not token.ttype in (T.DML, T.DDL)

    def _left_valid(token):
        if token.ttype is T.Keyword and token.value in ('NULL',):
            return True
        return token.ttype is not T.Keyword

    _group_left_right(tlist, T.Keyword, 'AS', sql.Identifier,
                      check_right=_right_valid,
                      check_left=_left_valid)


def group_assignment(tlist):
    _group_left_right(tlist, T.Assignment, ':=', sql.Assignment,
                      include_semicolon=True)


def group_comparison(tlist):

    def _parts_valid(token):
        return (token.ttype in (T.String.Symbol, T.String.Single,
                                T.Name, T.Number, T.Number.Float,
                                T.Number.Integer, T.Literal,
                                T.Literal.Number.Integer, T.Name.Placeholder)
                or isinstance(token, (sql.Identifier, sql.Parenthesis))
                or (token.ttype is T.Keyword
                    and token.value.upper() in ['NULL', ]))
    _group_left_right(tlist, T.Operator.Comparison, None, sql.Comparison,
                      check_left=_parts_valid, check_right=_parts_valid)


def group_case(tlist):
    _group_matching(tlist, T.Keyword, 'CASE', T.Keyword, 'END', sql.Case,
                    include_semicolon=True, recurse=True)


def group_identifier(tlist):
    def _consume_cycle(tl, i):
        # TODO: Usage of Wildcard token is ambivalent here.
        x = itertools.cycle((
            lambda y: (y.match(T.Punctuation, '.')
                       or y.ttype in (T.Operator,
                                      T.Wildcard,
                                      T.Name)
                       or isinstance(y, sql.SquareBrackets)),
            lambda y: (y.ttype in (T.String.Symbol,
                                   T.Name,
                                   T.Wildcard,
                                   T.Literal.String.Single,
                                   T.Literal.Number.Integer,
                                   T.Literal.Number.Float)
                       or isinstance(y, (sql.Parenthesis,
                                         sql.SquareBrackets,
                                         sql.Function)))))
        for t in tl.tokens[i:]:
            # Don't take whitespaces into account.
            if t.ttype is T.Whitespace:
                yield t
                continue
            if next(x)(t):
                yield t
            else:
                if isinstance(t, sql.Comment) and t.is_multiline():
                    yield t
                return

    def _next_token(tl, i):
        # chooses the next token. if two tokens are found then the
        # first is returned.
        t1 = tl.token_next_by_type(
            i, (T.String.Symbol, T.Name, T.Literal.Number.Integer,
                T.Literal.Number.Float))

        i1 = tl.token_index(t1, start=i) if t1 else None
        t2_end = None if i1 is None else i1 + 1
        t2 = tl.token_next_by_instance(i, (sql.Function, sql.Parenthesis), end=t2_end)

        if t1 and t2:
            i2 = tl.token_index(t2, start=i)
            if i1 > i2:
                return t2
            else:
                return t1
        elif t1:
            return t1
        else:
            return t2

    # bottom up approach: group subgroups first
    [group_identifier(sgroup) for sgroup in tlist.get_sublists()
     if not isinstance(sgroup, sql.Identifier)]

    # real processing
    idx = 0
    token = _next_token(tlist, idx)
    while token:
        identifier_tokens = [token] + list(
            _consume_cycle(tlist,
                           tlist.token_index(token, start=idx) + 1))
        # remove trailing whitespace
        if identifier_tokens and identifier_tokens[-1].ttype is T.Whitespace:
            identifier_tokens = identifier_tokens[:-1]
        if not (len(identifier_tokens) == 1
                and (isinstance(identifier_tokens[0], (sql.Function, sql.Parenthesis))
                     or identifier_tokens[0].ttype in (T.Literal.Number.Integer,
                                                       T.Literal.Number.Float))):
            group = tlist.group_tokens(sql.Identifier, identifier_tokens)
            idx = tlist.token_index(group, start=idx) + 1
        else:
            idx += 1
        token = _next_token(tlist, idx)


def group_identifier_list(tlist):
    [group_identifier_list(sgroup) for sgroup in tlist.get_sublists()
     if not isinstance(sgroup, sql.IdentifierList)]
    # Allowed list items
    fend1_funcs = [lambda t: isinstance(t, (sql.Identifier, sql.Function,
                                            sql.Case)),
                   lambda t: t.is_whitespace(),
                   lambda t: t.ttype == T.Name,
                   lambda t: t.ttype == T.Wildcard,
                   lambda t: t.match(T.Keyword, 'null'),
                   lambda t: t.match(T.Keyword, 'role'),
                   lambda t: t.ttype == T.Number.Integer,
                   lambda t: t.ttype == T.String.Single,
                   lambda t: t.ttype == T.Name.Placeholder,
                   lambda t: t.ttype == T.Keyword,
                   lambda t: isinstance(t, sql.Comparison),
                   lambda t: isinstance(t, sql.Comment),
                   lambda t: t.ttype == T.Comment.Multiline,
                   ]
    tcomma = tlist.token_next_match(0, T.Punctuation, ',')
    start = None
    while tcomma is not None:
        # Go back one idx to make sure to find the correct tcomma
        idx = tlist.token_index(tcomma)
        before = tlist.token_prev(idx)
        after = tlist.token_next(idx)
        # Check if the tokens around tcomma belong to a list
        bpassed = apassed = False
        for func in fend1_funcs:
            if before is not None and func(before):
                bpassed = True
            if after is not None and func(after):
                apassed = True
        if not bpassed or not apassed:
            # Something's wrong here, skip ahead to next ","
            start = None
            tcomma = tlist.token_next_match(idx + 1,
                                            T.Punctuation, ',')
        else:
            if start is None:
                start = before
            after_idx = tlist.token_index(after, start=idx)
            next_ = tlist.token_next(after_idx)
            if next_ is None or not next_.match(T.Punctuation, ','):
                # Reached the end of the list
                tokens = tlist.tokens_between(start, after)
                group = tlist.group_tokens(sql.IdentifierList, tokens)
                start = None
                tcomma = tlist.token_next_match(tlist.token_index(group) + 1,
                                                T.Punctuation, ',')
            else:
                tcomma = next_


def group_brackets(tlist):
    """Group parentheses () or square brackets []

        This is just like _group_matching, but complicated by the fact that
        round brackets can contain square bracket groups and vice versa
    """

    if isinstance(tlist, (sql.Parenthesis, sql.SquareBrackets)):
        idx = 1
    else:
        idx = 0

    # Find the first opening bracket
    token = tlist.token_next_match(idx, T.Punctuation, ['(', '['])

    while token:
        start_val = token.value  # either '(' or '['
        if start_val == '(':
            end_val = ')'
            group_class = sql.Parenthesis
        else:
            end_val = ']'
            group_class = sql.SquareBrackets

        tidx = tlist.token_index(token)

        # Find the corresponding closing bracket
        end = _find_matching(tidx, tlist, T.Punctuation, start_val,
                             T.Punctuation, end_val)

        if end is None:
            idx = tidx + 1
        else:
            group = tlist.group_tokens(group_class,
                                       tlist.tokens_between(token, end))

            # Check for nested bracket groups within this group
            group_brackets(group)
            idx = tlist.token_index(group) + 1

        # Find the next opening bracket
        token = tlist.token_next_match(idx, T.Punctuation, ['(', '['])


def group_comments(tlist):
    [group_comments(sgroup) for sgroup in tlist.get_sublists()
     if not isinstance(sgroup, sql.Comment)]
    idx = 0
    token = tlist.token_next_by_type(idx, T.Comment)
    while token:
        tidx = tlist.token_index(token)
        end = tlist.token_not_matching(tidx + 1,
                                       [lambda t: t.ttype in T.Comment,
                                        lambda t: t.is_whitespace()])
        if end is None:
            idx = tidx + 1
        else:
            eidx = tlist.token_index(end)
            grp_tokens = tlist.tokens_between(token,
                                              tlist.token_prev(eidx, False))
            group = tlist.group_tokens(sql.Comment, grp_tokens)
            idx = tlist.token_index(group)
        token = tlist.token_next_by_type(idx, T.Comment)


# bugfix Oracle10g merge and Oracle connect by
def group_where(tlist):
    def end_match(token):
        stopwords = ('ORDER', 'GROUP', 'LIMIT', 'UNION', 'EXCEPT', 'HAVING',
                     'WHEN', # for Oracle10g merge
                     'CONNECT', # for Oracle connect by
                     )
        if token.match(T.Keyword, stopwords):
            return True
        if token.match(T.DML, ('DELETE')): # for Oracle10g merge
            return True
        if token.match(T.DML, ('START')): # for Oracle connect by
            return True

        return False

    [group_where(sgroup) for sgroup in tlist.get_sublists()
     if not isinstance(sgroup, sql.Where)]
    idx = 0
    token = tlist.token_next_match(idx, T.Keyword, 'WHERE')
    while token:
        tidx = tlist.token_index(token)
        end = tlist.token_matching(tidx + 1, (end_match, ))
        if end is None:
            end = tlist._groupable_tokens[-1]
        else:
            end = tlist.tokens[tlist.token_index(end) - 1]
        group = tlist.group_tokens(sql.Where,
                                   tlist.tokens_between(token, end),
                                   ignore_ws=True)
        idx = tlist.token_index(group)
        token = tlist.token_next_match(idx, T.Keyword, 'WHERE')


def group_aliased(tlist):
    clss = (sql.Identifier, sql.Function, sql.Case)
    [group_aliased(sgroup) for sgroup in tlist.get_sublists()
     if not isinstance(sgroup, clss)]
    idx = 0
    token = tlist.token_next_by_instance(idx, clss)
    while token:
        next_ = tlist.token_next(tlist.token_index(token))
        if next_ is not None and isinstance(next_, clss):
            # for jython str.upper()
            # if not next_.value.upper().startswith('VARCHAR'):
            text = next_.value
            if sys.version_info[0] < 3 and isinstance(text, str):
                text = text.decode('utf-8').upper().encode('utf-8')
            if not text.startswith('VARCHAR'):
                grp = tlist.tokens_between(token, next_)[1:]
                token.tokens.extend(grp)
                for t in grp:
                    tlist.tokens.remove(t)
        idx = tlist.token_index(token) + 1
        token = tlist.token_next_by_instance(idx, clss)


def group_typecasts(tlist):
    _group_left_right(tlist, T.Punctuation, '::', sql.Identifier)


def group_functions(tlist):
    [group_functions(sgroup) for sgroup in tlist.get_sublists()
     if not isinstance(sgroup, sql.Function)]
    idx = 0
    token = tlist.token_next_by_type(idx, T.Name)
    while token:
        next_ = tlist.token_next(token)
        if not isinstance(next_, sql.Parenthesis):
            idx = tlist.token_index(token) + 1
        else:
            func = tlist.group_tokens(sql.Function,
                                      tlist.tokens_between(token, next_))
            idx = tlist.token_index(func) + 1
        token = tlist.token_next_by_type(idx, T.Name)


def group_order(tlist):
    idx = 0
    token = tlist.token_next_by_type(idx, T.Keyword.Order)
    while token:
        prev = tlist.token_prev(token)
        if isinstance(prev, sql.Identifier):
            ido = tlist.group_tokens(sql.Identifier,
                                     tlist.tokens_between(prev, token))
            idx = tlist.token_index(ido) + 1
        else:
            idx = tlist.token_index(token) + 1
        token = tlist.token_next_by_type(idx, T.Keyword.Order)


def align_comments(tlist):
    [align_comments(sgroup) for sgroup in tlist.get_sublists()]
    idx = 0
    token = tlist.token_next_by_instance(idx, sql.Comment)
    while token:
        before = tlist.token_prev(tlist.token_index(token))
        if isinstance(before, sql.TokenList):
            grp = tlist.tokens_between(before, token)[1:]
            before.tokens.extend(grp)
            for t in grp:
                tlist.tokens.remove(t)
            idx = tlist.token_index(before) + 1
        else:
            idx = tlist.token_index(token) + 1
        token = tlist.token_next_by_instance(idx, sql.Comment)


def group(tlist):
    for func in [
            group_comments,
            group_brackets,
            group_functions,
            # bugfix Oracle10g merge
            # group_where,
            # group_case,
            group_case,
            group_where,

            group_identifier,
            group_order,
            group_typecasts,
            group_as,
            group_aliased,
            group_assignment,
            group_comparison,
            align_comments,
            group_identifier_list,
            group_if,
            group_for,
            group_foreach,
            group_begin,
            ]:
        func(tlist)
