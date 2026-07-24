seeds_ansits_csv = """
id,name,some_date
1,Easton,1981-05-20 06:46:51
2,Lillian,1978-09-03 18:10:33
3,Jeremiah,1982-03-11 03:59:51
4,Nolan,1976-05-06 20:21:35
5,Hannah,1982-06-23 05:41:26
6,Eleanor,1991-08-10 23:12:21
7,Lily,1971-03-29 14:58:02
8,Jonathan,1988-02-26 02:55:24
9,Adrian,1994-02-09 13:14:23
10,Nora,1976-03-01 16:51:39
""".lstrip()

seeds_base_csv = """
ID,NAME,SOME_DATE
1,Easton,1981-05-20 06:46:51
2,Lillian,1978-09-03 18:10:33
3,Jeremiah,1982-03-11 03:59:51
4,Nolan,1976-05-06 20:21:35
5,Hannah,1982-06-23 05:41:26
6,Eleanor,1991-08-10 23:12:21
7,Lily,1971-03-29 14:58:02
8,Jonathan,1988-02-26 02:55:24
9,Adrian,1994-02-09 13:14:23
10,Nora,1976-03-01 16:51:39
""".lstrip()

seeds_added_csv = seeds_base_csv + """
11,Mateo,2014-09-07 17:04:27
12,Julian,2000-02-04 11:48:30
13,Gabriel,2001-07-10 07:32:52
14,Isaac,2002-11-24 03:22:28
15,Levi,2009-11-15 11:57:15
16,Elizabeth,2005-04-09 03:50:11
17,Grayson,2019-08-06 19:28:17
18,Dylan,2014-03-01 11:50:41
19,Jayden,2009-06-06 07:12:49
20,Luke,2003-12-05 21:42:18
""".lstrip()

seeds_newcolumns_csv = """
id,name,some_date,last_initial
1,Easton,1981-05-20 06:46:51,A
2,Lillian,1978-09-03 18:10:33,B
3,Jeremiah,1982-03-11 03:59:51,C
4,Nolan,1976-05-06 20:21:35,D
5,Hannah,1982-06-23 05:41:26,E
6,Eleanor,1991-08-10 23:12:21,F
7,Lily,1971-03-29 14:58:02,G
8,Jonathan,1988-02-26 02:55:24,H
9,Adrian,1994-02-09 13:14:23,I
10,Nora,1976-03-01 16:51:39,J
""".lstrip()
