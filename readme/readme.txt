Formatter for SQL (lexer name can be any starting with "SQL").
Ported from Sublime Text plugin.

Uses uroboroSQL Python lib:
  https://github.com/future-architect

UroboroSQL is often used in enterprise systems, for formatting to a highly maintainable style even for very long SQL.
In particular, in countries where English is not their mother tongue, such as Japan, comments may be included in SELECT clauses. In that case, we will align the vertical position of the AS clause and the comment, pursuing the viewability which can be said as artistic anymore, This was developed to realize this automatically.

--- In case of general formatter
SELECT MI.MAKER_CD AS ITEM_MAKER_CD -- メーカーコード
,
       MI.BRAND_CD AS ITEM_BRAND_CD -- ブランドコード
,
       MI.ITEM_CD AS ITEM_CD -- 商品コード
,
       MI.CATEGORY AS ITEM_CATEGORY -- 商品カテゴリ
FROM M_ITEM MI -- 商品マスタ

WHERE 1 = 1
  AND MI.ARRIVAL_DATE = '2016-12-01' -- 入荷日


--- In case of uroboroSQL formatter
SELECT
    MI.MAKER_CD AS  ITEM_MAKER_CD   -- メーカーコード
,   MI.BRAND_CD AS  ITEM_BRAND_CD   -- ブランドコード
,   MI.ITEM_CD  AS  ITEM_CD         -- 商品コード
,   MI.CATEGORY AS  ITEM_CATEGORY   -- 商品カテゴリ
FROM
    M_ITEM  MI  -- 商品マスタ
WHERE
    1               =   1
AND MI.ARRIVAL_DATE =   '2016-12-01'    -- 入荷日


Options in json file:
- uf_tab_size
  Tab-char size of indents after formatting. Recommended 4.
- uf_translate_tabs_to_spaces
  Replace tab-chars to spaces.
- uf_uppercase
  Convert reserved words and identifiers to upper case.
- uf_comment_syntax
  Comments syntax format.
  You can specify the "uroboroSQL" or "doma2". In the case of normal SQL, can be any.
- uf_escapesequence_u005c
  If used escape sequences with a backslash in the SQL, set to true.


Author: Alexey Torgashin (CudaText)
License: MIT
