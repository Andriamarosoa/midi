#!/usr/bin/env python3
"""Fail-closed one-shot creator for the reviewed H27 control bundle.

Importing this module is effect-free.  Real execution is possible only from
the separately published immutable administrative source, with the exact
acknowledgement and paths sealed below.  The repository copy exists solely so
its bytes can be reviewed and bound before that publication is authorized.
"""
from __future__ import annotations

import ctypes
import base64
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
from typing import Callable, Iterable, Mapping, Optional
import zlib

try:
    import fcntl
except ImportError:  # pragma: no cover - the real entrypoint is macOS-only
    fcntl = None


SOURCE_ROOT = Path("/Users/amcarene/h27-admin/creator/h27-reviewed-control-bundle-creator-v1")
SOURCE_ENTRYPOINT = SOURCE_ROOT / "h27_reviewed_control_bundle_creator.py"
SOURCE_MANIFEST = SOURCE_ROOT / "manifest.json"
GIT_DATABASE = Path("/Users/amcarene/midi-worker/repository/.git")
EXPECTED_EXECUTION_HEAD = "7ee0a8977208bfa389e284b07207abc40a3517fd"
TARGET_CHECKOUT = Path("/Users/amcarene/midi-worker/repository")
REGISTRY = Path("/Users/amcarene/h27-admin/registry/h27-control-bundle-creation-authority-v1.jsonl")
CONTROL_PARENT = Path("/Users/amcarene/h27-admin/control")
FINAL_BUNDLE = CONTROL_PARENT / "h27-constructor-execution-gate-v1"
STAGING_BUNDLE = CONTROL_PARENT / ".h27-constructor-execution-gate-v1.staging"
AUTHORITY_ID = "4e1072559ff1ef5ec1e2fb0e4ec72b3baca2d98811fabfb568e9380951129c76"
ACK_ENV = "H27_REVIEWED_CONTROL_BUNDLE_CREATOR_EXECUTE"
REGISTRY_NAMESPACE = "H27_CONTROL_BUNDLE_CREATION_AUTHORITY_REGISTRY_V1"
RENAME_EXCL = 0x00000004
AT_FDCWD = -2

CREATOR_ROOTS = (
    {"path":"configs/harmonic_censoring_h27_control_bundle_creation_authority_artifact.json","git_blob_sha1":"9f8ebc7c89502dfab04b724d8da173e647758365","size_bytes":920,"raw_sha256":"da2718b4349a6d51af1c5b1c1a1f86346d8f80e9b419283d58af21f8270b78d1"},
    {"path":"configs/harmonic_censoring_h27_control_bundle_creation_authority_artifact_external_seal.json","git_blob_sha1":"167e772f720cf6cd1bd4a7dca390c58d863711a5","size_bytes":2003,"raw_sha256":"40d742e38cca7a55a2ee39769ceaf71e9d73ab6f22d25e3abd9ce9590829cf86"},
    {"path":"configs/harmonic_censoring_h27_control_bundle_creation_authority_artifact_identity_binding.json","git_blob_sha1":"2c1d96a63ea76007f7ab3d59b044b5d38692b7af","size_bytes":3730,"raw_sha256":"e39079c505b7a29b38d6fc1ba0dceede13ac5a23acdfcf182f84a4a129d8d5cb"},
    {"path":"configs/harmonic_censoring_h27_control_bundle_creation_authority_artifact_identity_binding_external_seal.json","git_blob_sha1":"47244bbd38147a3231f327e70a6dcde3f4343b40","size_bytes":1400,"raw_sha256":"13ef586bf860984758ce030541a6fda7961bf37a93d27ab9cf3d2eb05609a9dc"},
)

BUNDLE_FILES = (
    {"path":"configs/harmonic_censoring_h27_real_publication_authority_instance_artifact_constructor_execution_gate_contract.json","git_blob_sha1":"1bdc95411520793c2f1ff0c08ef2245e569ef2a0","size_bytes":6387,"raw_sha256":"0134f4c459ac9d4e642da70dbcf257f34998db064e568ea0e039b58d5952f215"},
    {"path":"configs/harmonic_censoring_h27_real_publication_authority_instance_artifact_constructor_execution_gate_contract_external_seal.json","git_blob_sha1":"099703d92d9cfd761f5aa9065467fff1516d5a46","size_bytes":1673,"raw_sha256":"6cd9cc7f67c60ea71804fd01137ee2fddd1947c0fb0e56d3bc7d0db362054778"},
    {"path":"configs/harmonic_censoring_h27_real_publication_authority_instance_artifact_constructor_execution_authority_artifact.json","git_blob_sha1":"fedcf0f1c2be368ddf619e8f1715a55f499815c8","size_bytes":688,"raw_sha256":"dccc4afaf20390fe07226fbfd237c06b381b203d25f6f80908adc3753c985296"},
    {"path":"configs/harmonic_censoring_h27_real_publication_authority_instance_artifact_constructor_execution_authority_artifact_external_seal.json","git_blob_sha1":"4f3e49d29e5777b1ad5174b24870ac21f348ac78","size_bytes":1683,"raw_sha256":"5b2b985f694b1e360afc9aec84a6ba8329cf6bc7b4cfea106a67108ac550decc"},
    {"path":"configs/harmonic_censoring_h27_real_publication_authority_instance_artifact_constructor_execution_authority_artifact_identity_binding.json","git_blob_sha1":"fe89c67096bef9e41a0405a1e37a291be5fd1afa","size_bytes":2986,"raw_sha256":"8e9549db0821ed3f0334aab369abb18373bc5e2141d656b8e0c0e5ba6a65a9da"},
    {"path":"configs/harmonic_censoring_h27_real_publication_authority_instance_artifact_constructor_execution_authority_artifact_identity_binding_external_seal.json","git_blob_sha1":"3d79c43ee50ccc9b2e87c3c07d63a2061b18edbf","size_bytes":1431,"raw_sha256":"95892205cf7af0d84a5ec75b466467486eb50996d4040bdca7d25e4b9a58940c"},
)

RECORD_FIELDS = (
    "schema_version", "registry_namespace", "creation_authority_artifact_id",
    "transition_index", "state", "prior_record_raw_sha256",
    "expected_execution_git_head", "creator_implementation_raw_sha256",
    "bundle_manifest_raw_sha256", "failure_stage", "record_id",
)

# Generated once from the 130 exact reviewed predecessor identities.  The
# decoded value is canonical compact JSON; every entry is still rehashed from
# the explicit Git object database before the registry can be opened.
_IDENTITY_GRAPH_B85 = "c-qZ<+mc*4j^w}8^H>i6k{~&6^9O4-k85i(5+J*BO_wrB)w4Zo`|s-rsiu^1q|AuOOR4%Il``{$4hT5hNdWwx|M!>o<K6n@-+mdtfByBu$Ggw}d^0|NzT3k-|MD-t{5C%Sim%y+_xtYepZ@jN@$ub<_jmTj*85NR=J$Vp^Q+W1`10qEAKt#1zrXjl>y3R}<MZ8z_iv7m{M-Nj^x-|8`*Ho_ZvE$S{OG%Pcc1YQyX-uhl$n@PYHB0ZT&#1MYYG{aUE8LOA720G^ZNLHynXZKDR2I<KKh--L;lCV|Hpse8~%Rx`OSR$VZQnF>tOtG-)&8+)_NiFJtpN@C42M1H7(7xmX@^OM?c;D*LpMm`FVZ%<=?sx{-)zU<1tbc5Aq?E+srBVp<Z}wwldjx@NSy2dfSawpP9R~<fV-*_>xqbwK@Ot|Ni9xd%yYb7yGov+ZV9@{SWwKEzYgQT34;IE3CfNoTuke9ShRQN^`tuWgh3&5~6fwu1sFDtkld#9i<FeEA^_~*4UL-_nOAkE#guZe(U&3FP)lngFzoL*PXBTpW{#F-Ft^MUczGMpYdY{Zd`Y^Hm1Nav}WhJ*6!Lyr@9LFVPa-CIj|Ue*P&^Rszi0yG2vYuj+|$4giDuM$39z<RMWW!!~Rse6)O0C=`%IgZ9E6Lt>uf;Fsu{)-?wdUvRfW`uyjOAv3cc^yu3?4{E0vE@r>}#bHZ|*>qwG#CxP1&!rFYLjSx>W)0sgz)44%8tzDW<xGVLR0VK94QOP`X`>0)c?o>xlE?71AHGZ=u6@2^XZYP62yH!r#`XJuQrrNOZZe*j>Qo88|c%?0P3)^*S+xXut?#ciU&BgI6fDoXbR%W;t4JIvP%*|DN^fT)!3!ek7!<J2?G@gAc{=&*Uf#bv0WNNmzm1LeRbFz^+=Pd@r=?PfV+RIw^GGA+zfCE)`p@od&Jd)=QUl<8+YLqt;T$=0L*I=VFYhZ0O@0mzvYYi}M3mK78PYhsnKrBAN>Q*gfBlWCAo)bwclep#nZSbDI<{$5LO^kl}{PB1D{NW?)u<ZBKWBxuquOFK7aj#sh7GzC?V=mjb?18Mk;hM-0LOObzPTp_wO4_HqjLcP5@5oDY)zm$KR%Ega6JZ%jN@wd(;eTiA&=Dm}r7Qk!jfca(5#lMamuw_;_C>i&^_*=9P*n=2Nr?P9cQv|X9d1X?TUX^mZ|){(A=!hE=~|#Xy?A3;Eg^-&|G?Oo`vEyiI*;wy)|$0unuucpO&V!6E;W^0RwO7u(l7uCv8G0V5-=(Qw07>5ce%)lPvHnR8}f3}U`edDVjz~g!Tl_)+F%!?iM_|D6)XbQu$%lnA?^ogC%_;XXxP}jRmLawR+iFS09<!FCk>+KD<z_~4H;4T?rT>p&;|qp)Qb`L8&-VotUX)mb1W<)EpEQ{LV)D^wD)48{RIJV8<(i04nl@(Z#h*Y2<cj;z&-;hPqBzC&63)IOVo0X@2ex{PT&-PPI%3M(6Uk+=p#wmJB<b|*;(2|q|GsNK~RWDAE0mkt)2gT<7+@2CVBhjx8LX6J3G&Qcd+YtZ|hzfe9+VnBE8N<1+b~L=LL!hiklL=Dg*OnB-%qGW$8`)1FQy5VlD!*3*X<oHzZ_RkQxCl3NMy%j!{6FdbT3ODTCGL0`}fLLn?x|RPt$CO5M<bz4;`~cxGFJK>hlJMk>7slwbMbirnbk&%HjEc{uf6DR~#@v+Y#@z5}X8OV$dULij@rkF4h&uJv3ILQZxIhEh!lVul;&j}vo(Sd#7T+`&F+!@rAqf@(*;pGgIb8iDj<d)^H6&u-Go(ZBeFzh_To3xc~1klY2@nk`UsGzX7><E>j_z?qlu7zBDx-5IzsS6&->5o)ADL*fJbJm=sLMCUP3_hiA3LFE*cya!mQ=Tdty200qsz{F|vtgVl|6)L}MhJP#ut<rS)n*A(6aa$gM(4SqEkW-WOOrWkQsZGlR_5dA3jt99p-#1~T({qc%aNIQasjF9$8sZ*WpItqe5AuZek;w(p99)RYRx^-ftTvLwJ)ZyPJ3e89?-?w7&0Zk*c@gfTFnq6q_aht%Al9v{3>31a&D(8zfqS_@G_lEC36Jru+*gAl<pO1}1JOZi&a<_)b}mg}@jN0Lfcdl+RnVk8w@U(m=|m(=e8~li16|z_DPXS^Y8CVg6yefE`s;$?)(ynGq4&E>U!~SMLm+|0PRUThU`LF!*+A?Mgh<<Yx&V!uu+|2(oQ&n7v8@lV$~<%qFdyV2MUI$2%oUppLlHZ8cq!z|>|z`LmD%G-yN+ehY@R&rM7*H(OP$WGfb1h(P7itod8@aD3dEjP>fmbN{h0@4Dgz4<TZcRW^T<+roNom8rf2Ke5YX@l2tBY`{9P%fJO<KwA9I4iRwVj@bQK6!6v7Z>Z9%+XJ<I4mZeGWqDtK;7E6Hnzuvn19K%73Iw2@ehs%sj+Muq{G&wY>=2f^J->jENWP%E1pK?G%4%gm}Ea=Gc61ym2o9qSAVJ!)*r=LsNg$Y<AVRlbY?A6FHn%-9A?2?@k`0eOP1a%nV3b=5-P{?MeiZNg6=dlqSs<v^R38?(9U2L3e9bvUK$^K2nX=X0G0^ePEf9eDxV3UTeob~?4{a?t8l5og;cgat6q)<{jEB{g=D7MAI!S%?b-@&d~zjZIvGo>fOar)CX)OQ4$oE3lZc(qYS}pBoOeM`a_q3WF07+f-6(lmyT>6F5V*Y7XPJR*-94mey6WOJ+^8{XB;I5yBsAhdA!Lr(JZP$jJosx~^6C0*EfW8ElcxNhQ8?IH>4UX9I|LUmL#HXBq}6w=L;uGiXDM<Uke5*|9LX+7uAkF~GdC|Gc)l%nRWm&?woV-gAfTOcm0yA{pfon`7D#;DFlW#^t#sNsN&9NUH9R)W+7k%%W<&j087JCC8b{1VtV2QGhkHtjU06%82Q2v)SGIe|)%ar2o2cKmKN;pMLPszsCaypQ%Z%0NO#Zzdg$;21{=I5mG&{Y;0G6*e#fAMO1v|oTm|JbEb6KfvA--h)Gtc*)flp+tN7&0p^raJtdDl9V&IS3`yo=gVD5YSgr~sRpX4>4M09SYX||zIhQ%FTC~@u9hWWPrN{p;MJla?zK00ioa+S5tX6c<?o4Y|Z+wW8L$ySrHhX7J!)MfPu$a<zkQV3x28#zHtX|ew9_QMthh73t1hz9W>UDAQ7f|>Mt$sO~AGN8Mnh0;-pn0k^YH;NSQ~`Hsc|)h-ceg}R=@0~=z-E&LhNK{UZGech1@*81W*wih4^<uga3-6fD!_yi_>U~vU|bN;I$a=sji;?iM6EX{Fnl1-5vh5Bzd~{sp6zMN`jdv%jYkIwNlAb^wY844ZnSeY$rI_m1en_B(75%$?fdzWWQMw)Gfvt2B8At80L&`24d81Pnk-I~AR3VBG6ePT-pvhgSd@p{+ob#U_1}H)-`}o3&HU-3{p)WZ-v0BqU&F}HZSBAP_RsGh7TC1SmMi{&G_*3ILltD6vn~O*-!?hbdDAhO;r)k=EHe(=Af>$4F*B0<bdc{o#*nFUz6MfyKPLvW4M&<^8$7qhp*u<JF0H*PRuTwUyr&En3w?qBNwX6nvsr8pHmVOV!s~0<`<DFHk&jE{n+)_+K}(q%_Zs^)d*%TV2A3=Vw8rVS^Bgd$2F#fRxjK`3SEP>$#F<4#8e2110RH6=Cgpt74!Is{!_ZQDH~cywbxUl92UXj(C&7aj!VfXn#Rf=s><)G)j+qkgAFa^qC!fo+%1f?{3Q{~$0QkZHQ-(A{=8`5Le_+N2b{4fRT@Qt6be>hf8YePKE}$0zT9!mX6hgyoO}4Pa3@Jou<=Vx^ptM!6DiKi?U%PZ=UOS2|OAN2OYGrY#l}0^qw2PDlb)r^i*KHjJ*BYfThm(rK`Dg-%Bcv&?aV$_Id`%+Y)Ce)A(F^{~vgbx4<*1SypaKQbi;?am{V<+hfYp6?zwr0|@cHtUd-vPh^$s6@A)h;<)@p#OsQ)n&<mIJn=e3b$fIbepBSByt&SN7V>b|meXiF&85m_X4DUq=NQtGLtUaifjrG>q<;B$l_@gZj#D7CAPdbO3GD@b0<<`>ed#!%{3<0!%aOh~^wiXOotavey{TuXvpJ<_Z5%noWbO6h4>)Xq|G11pKutE^3BcZzED76+<Pp0?76Vl&B>n)NxXK4tUdxs3Qg6;g}C$_mKM%T|I0+q~N%yzVk5pgMytp6Vs8#u|vl1bI+0Z+0pZa&Yh1t`oR)i;COH1{Qj@2ATWeFsM!66Db-&#acJGm59%g5k%sW0}|J+AXOPUrjG%Z3<(Op8|T#Ae}*-<e5)#oAF~2HK_$0$UPVr<owE2Y4zhp9s?2;Y!K*DIS&d;T_9#xYEgi&&Kyg>pqc@A4XwHiP`Z-Se!B8Q}L9ynRd*$Be8*$Hz3!gsyzCQl>mDA6BZ$I$6c7MddDVhsx$M$_E=pLH7*7R9+2H)Gz5y+-nZaNkKo8P7t<TM^E*#)>FU@v>h-chO8cu79j4~Vwo4s8XQB2R>eOfG%4*wBXVM^GY4Ah2g&fG|#QhoK`)A;z~V78N?~!Nqz>NPqg$T^1KAr4-j{&`m0Fj2=i3dxO;-$#l=<tmCKyayitMC-9%ODsZhQ+Nn`1RW*Jb4`A@ux_TuYOIlr6-!(dw02z48SPz@}Wl763So?DEAd=GNYO#YWjgc4zHBG&NjT^E96qE=A?@cr`XXkKU1Dz#l?yHYp<9K2s42Jk(rL_(O=}?f($WNvXYGCG6SvD`|b4DZzBMvh}ePg^yDPu%S(}v7nMe_#DP0@&O)pGvip>*T%2sGIgD5^0_lwzulICI)5l(0qlWD@~y9*;-P7X$h)RT;=7J<ZG-O++I>OCxYVkSZV;LJnCiwy9VgKu1HTH!}0N@9hshZiv4&89knQx|<gQ6E9Ztrew7C%A+DDbDeXa&g8t^q~kIHruN|M$)kK6@<8DD{Zyn^=SmV4Y3+Rbu%ts5lL?k8y7IJwQ8l+7NI2`1+JUuA(pWrW&ub1)hXHA`WC$2S5~lm7BbQt4X9%S0GEj1)8@&6J8GTdDD%-3Ujf^CFMJuRDv%_X#Zs#?AYbQ^Z=c%-9l&Kl(*YUGy&!kcF0i_|ms0n^J2T^HhC8`byX)WDo@t-3#-H?c)y&$*Jo6?4VLOVm@E;xGZEKILl5LnQAH^mWySdoAWB-ovh{~P`j`M)UgTLLCd<D3qM?Ai|<uhHWcb+1ufXmf$R6_2X$&IyzoE;9k5yoFoOntOBZdqmA3R8lF=w5mT<VBMCF2)LNNAtrb&iL)a|1Rw-l5Eq`(+#Tp+$F7R=NZXKqJRvt1$Xgq+kAh%Y!Tre!GL_^CX|N=CM^2nZ>UktB37mfPd*tBDX%I~CCHFq_iT#hweaYuO5IYr2nH0z&oo1ZFcFU07(RXCjh@*Wl=iBz?>oj<>jJ0C7Wi8Nhq%|kV{arG3nc4fHHMx{}><3G&RY*~)Dxl`QRKinAStIL8Wr3i(1e4p*vp;higjh0)H`}V$uG7m0$@PDWA4LN)y0+3r?l9#nAWj=Wu}EWEssOh#(y$$i0D)x325_XD3LUk9cFnefjkF4$--hCuv*P<Y@fbCl_lI*WyT*T1cN*7Q`86`mO@EOe$IF!N;H2ELGBkZzPLzNR25y{SiX8o&#y1@|O4K95&{$9zBRevEYH)AlGRTpvh)IjEJkK=<io-C97283s_;Jk&asZIy8ikJTrC5(Xn%IK$9sBW7(y?qacnV0jY<lua{v-i(TYdq*n!RsZeS>Yq_Q@I$K--NK3X?>m^>QD|T>9}0q(UHtguxm@-%LVWG17eQ1uT3;%kqeM4Iq5@Owi^+Ak~$5ZfNNHeXMKmg;&}i*ZRW-&vXL+LnHs_%pGLQ67;kq3i`?o0wG0nulp7nkOAEBHM(t6xSK)tEp?TKNa(?xi)V34&_c-i1KQmV2T+vK`L3{F@dRNs3Un&PY=9BnmR&4^v85pp`?3h%-G?=&nc_s(Hbwa~nBzs(|L$4%OE~;PXYL0h)|fjZ(UPUzQpi1tj;;kg(E`GoQS9QL8xaOLvmw;zDl{ESJ8H2qVhjlQ(S}U#DQZN@-gpwkh(X-UXa*bu7@4@UmGy`XUn2ut4(=V~g5l9phD~U2WYtQm)qyB&0C}Pe9qn>c$3z^=#Q>P?+Xj%fI&=v`uUL*Y3Ld^$>!Ilmt95?Z(TNPgGEiICJzE@AHHsP@$+N<jAtOu^JXt{s7NVdcwcz^~TjML2<mI9KMwBkJT@kv`6VkfIez-g1g#bjHp`Y@I5`=RfZwH*v9p_Cg7Yb{G?GhNP<UT-~c)Op<p{oP(U`(V){F2u0ZM1<P^ZUh!Utj6M!^#&i=MxX7i9(--6yg#)7_E$WeSk6fj5;gMNMqxC?^S9!m%LSjhXl};xo71Bb85q*r&QQ4HRM4B!vr*A1@R9=F--0;yU3u{o?zHl@Y-iRj~0zhzt%>yHd!u9Dg;@9-BafnTeE=Ml@H~9EaxnK0_q8--K(Z(3rK))`172K2UFuzrL7J)2aL}h+0-Ed!BBeb_)U85v(N{v^<yk%g7QH4w#2})1;R1f8XHFGT9K-&Ht;68Y1~Vl(4dJ|M7F~L3xtkPE<k)8AU6uOy&!E4rQ`k3H$_n=>%6cKLvkW47DX@7VseYx_u_a3B+EEcpwd)0?P!o5VEDqXYU~S7(x4k@%kFhUOe537D2v<fnvfnL;YY#0)FT0Fhk;_DDp~^rX85A@yo^Tk8s{!0>Kmswc=v=~uND3Ze=k!vl`cVx&%^)whZ@fw+t;2T&(u}hN@h`ls=Nt2!RK%_kr^W_Lc5KdnjC88uDeCCcZ?E4;Ere|gM`?5so@tTaDekZ%aRZMvK;Mi*@q)@S?v>~9Y3hRj}{v=$YgcL5l_{=SK2d+A{~O)myEa2ec58X4B9^BU^wO^fE7Tfq}HseK)FR-2%ACw5-2jVJjm4ffX8&M<)E3hRAC?m6p5L#i`mw(M{hCsCR7XeQIYHr^tr%*SSfHa{A3^HLIb`OF?jNEFCjXCifj3vlL<Mx03>2E6ZhDlZe3E|t>5D2ZE1(37+%JN?{=v+w0rE0Psoc>1Rz=um;;V>zM~6uCylAlh+d!~5YeNLmLai$J6(N8NA#)A2m+S#P{n!z*eyp7<&~@Ss_uRpv4FbRwr!cZbel+2jCkIIz%EGRI1d()Q+>;QI6o9d3^;X6(2Mbv#L<EPh?~4(?p%TP3%xWaph^tt2E+w$(-sgA$d~{--=7cpA~1eIXBu40Y(dO%Z@MkI#<VkHdiNv@j*8!>e$$yz6$l205Qz><jdFwBVxl8Co5#o}aF>_^a+G=plS9iPypUI-S;JfC_Cy0=20tIGb^LYNSMN2}vH{AlZqXhB)!z%t!zO=z@4XJ12ircK(19jd+a99Jtn{5{vV?GqLA)a8cIt-%)6p1SIl>=7VWDVeG+U?Dv83IWGf=qZ((_zEfDV&&t`kYr<A6izBW8LDNWKApHPLMBJUm*xki8cud(3bH<!mX+y@qVln|9qQcx#jcNa?Q9JqF8I6HAmq0+0-o>a?bZ!M<G&gD4xk6F%x0e!BW@gQ5o6%+uBttI%Wo5WdO;l1*jD6k+-@+^eU{*5U<S_trDX8I$dD9i}ZiLRFQKBbUGli-4>ZxLUIV&EP|cOo<Xi^B7!GSqXeOfiP=KHldh!ajIEPU~KMdR;u8a$ZXYWv}EQ7=V9D>9Jzo0{QF1zr9a;J-;tW^^W8tbwmSTgr4A;3?6V&@l3a@?($>nUyMtK(qf3k9JO&`kqG<2Q+i&u74VhO~wz)yow)kj}fGvtDSCmsge+wV7VTSlQKhAG+Y=lass1fy?HD(r+p^M-LeW^mQ)){kImo6mRD4hjFSEz8U_o4YQTV3bvFR)k_;`su-+8y4$drTnQn__lIjd^+_6=(@r%kntxI-di&y80|>`b7H6SSN^{P&)-rrk=&M;=c|5t23rnrb&?_+lq0Ptm7)<UJLIpVc#nbAbXC^0RyY$xdeV@(NzNx-BvUst}@J<-$Yzk5p}ZDtjVoF&a{{~SD-&vn}uUyL62c0=UG4x2VWegq6$Tnt2e047&;8!Z>O_^QSi%xoMMin0|Kv1$ZRz#*0K)3UB6`k|N1DoEp=?L95{U4?qEHq8P#xo@$TE^+%c&JDqN2YUC+xak!_uIf(%*(6|Xw6dSF5vlcmA_fqMjS-AWsej)L?FSsWc0F+!x=%e}rneZG7DdimmepZ5TLFWY+PxYA-~06a(PTvhh~O-X=;&0rekwiY;DvqgB>cI2Y8vOva1$1a}QC$PRjH1v5W`8w>mEGB%v)G~&GZx--V2R{db)sYmyws?)6OX@r7k4a<3X)B-r1B95@W9xC_CigR~&V^->tX*P?UMdhk1M(Bpa8s9<o}pz9ns8b>$CQ2;Qj@Ua6W=dWz*1pZh)jr~IbhF@)Z)-eNE1~OvXB86BNss+K|}3UDnDw>o6lyR%bu4fffdv2BB@dwSI^VYi74D>t%(<pdR>T5zRCULM3-is;kcQb!^oxf@X{!5O?6KIlnyz#|6v*g7NiPN6n7wcucIPBM_)Vj)MG+)?EVty(JnC}_EgUYVwX0p4UBpmj-Kn#=cU%~!VOAAyaS>8)ESx!u*HxKal(jy7R;8U*s6!5o6}*4+gJd0r~yW%McBnSt;*Hna5OQVN)}b61&kM(xS6F45m|GclKvRu^wr+Cm6qIM$qygjjrX6wl$soTac+eMh%tafeRa<TY0YEii7e!}3brChlIIOn`7n|bcmQjHjZ}_O21qGdN~=-L%VNq&2bZ64z8=FOV}eARF~XeUY8nXcqitT^$G%wRs=^Q0D#fUENr+t}elX{leu?}NJ8*zZB~Y*9IOcS8CX2GR%&BQKpQSj&0)rSa&xNOqWZ5OnqKTr`w#B&Ay7`37NM_%0rdPq$uQt2%th=knQ2SCyXD>0SY7RsRNYocYA^FF#>pAy|LZS2YB)P<P7EDw6=&1<o5~cfza!pu^oe9|w;Wr^XfrbQn230iI%DGwlvAtf+(QZ7sUU{|JI0iNWy|lnhdT0D!%#p^M8bGOygUhvcC>JPzs)?1z&;q(_Z0}Lrh@VCxDqkjTj5wfmnpN<%3~yUwv>k_5$7<|vU-B<W^G_|s$dJ53EyhEGke197oVOZCeGdAQ;~Irz>AVuLz~#;rb@v9~Z@{|Q7i@=z!1c`$-3abRQcjYuQ^D6qfNjaq(4IA%m~OM}>m}spt;XP)d-P1D8dED;VKx(_paBU?EjrS2%$}!1CGNrQZi6G;3|^K`o3%UHUZf11*%Ocet)WyaRLd&OJS28iR@2t_YnSzFTkV0W3}%ouvj*ajd8B1=qnSiC#c8TkSSd#5efz_|jgR<*Z?BhXr>^{jcW3CL-OZz0A6YoZj$Ftsq-(zEAkm_5Aqw`U!Ki&YN3X$(k)Y7NMunmr=`g|@?BcvN1UZzo#U2X;8N#9hXh5i1%%$70E4~asUkPfR9dHjlPNue?@OYN|mn__+d)2G89W!-mPLcCyP+W7iB?=H(%icWofGU#Ye8Zts5UCv<Z%I$p>yXL)bZuJPeTMvZy2zvF9J*ZNkbKlQS&ZXHD7<^8t$$>pZ(sA%-Mio4j+p-SQhfAcDyl9eTJ3@tHo>BAxPf%$-H0Rq^pUmILz;^!fOFRZLn{dKxUwr1@bwvc$6)=9n-;caSQ?JYlfLx(FP?jzc0M&W{_R?;J*`CfCL3NwT49Npi-uR5eU3P-o^_jrSz{DV>Igt6&VxT5Z$WFLMU7Q-=xZ*~{+HBYMX94j=@K9{10H(THDLM?EzD+}1#Wq|XYFFkz95Tu3ZG4ZRn@@`7U-)YcR>d(LvXehmy=o)IRL}Y6Bi$Qu0~5^XNfcC3ev$zwt>_&h%op%MeRk@QH&xvLpNoq47^-$*B<*2{dQZv7;AVw(z|Rs)T7o#;w#2)f}yIf<VfojRmhuQH9OSE9x4c-FTunlr5RVxE}tv672OqJ(#0}D;dC{~`m)KBqDpIdNOqHq-`*=e{^tGu_AEwvfsNnqJ^qJkHj`+TXt(UEBya>;Bay7K5@*PGUQv^DC<_uf=>H~@X^iDDbzpOYkM`LiOiJ90U^eC|vEvJck#oRMjUlv<GGK35U3nEVzl!5u*<ILT0yack0mlPO537A>5sxDV&2jHr*~EuI9D1lr<{1AMXBuF*JBr1?9v69n1R)SVjlcn2qo^+HAZ=JM)zzY2FW6yy(G_?lIKLFe4cazA0?$)LoEB|JUVTEq<wj{y4xkx(9U0o8?L5^EQXCs)EtR;ArVbe~Y0f}ukrOQleI^aCZ(~-5EWtWsk?M#}tXDPrs|3Jpi0`y5r6^9yx_wn3G3NpCT~{tK0Ceo_Egz@tA4tl=50!@Hlc;jw4N~lJO=1NlObwJ|)e5*eRgUBq{c5{`u$LV-Z2Oe^Qv9pP`Xilv@8w^LJ3q*mrPc*f8;vAeios>e<amuZ<6W_tG1F{v98@N9UQ%SI2_wmn^`cO`#2_Fs7@ZQ5aE8yTgOx`)RLoL<b|10L+l`{Myw2}2kssUXrP=aL3^~(|MjR50t4d<dhpxDxzLo$_L~M==>ko;L4=p)Jr+Inf<*Q5Av}!i(;+(fz0li~jajR@O&LL|I`zuiw!%>3U8(nG37sS<TsqxsA1l(yiNC1lI&2jG|(tn}iEo~mw;vV&5zZf5Cv_e2YI^f$O$YQ342+0J=E=Z0V1NdCQQd;b_@s?EK>qR8?(=%Crq7h#VC7;HLH;iet+&FF?k{EM22HY*0>6~UXl0+Zb`9YTEdhVoP6g`N*fQD%!S93~|V*2dLDNifVAU0LZb4?a~y~tz8juQ$z$Hv9?5b}F3`~v*;F;2THByL<*z9y%(C<ZII!w3)$v*3@ZXRk?)R{_eQI=E%1t^o_jU?v(hf#G`JJ{?3MWmqn1zBM)`ih}mGT2IHY1Vz}!y;y$eRbI^BuH3eY8wCn9eAUvMFJ94{*rKuky5D0)99}K^;nLzmjcWIpA6E<a5veuBnKOao&Nz@sA|-AtNbse+;<(h3v{hRS4prDz9yQzxqTa<5h5<ZFVI?=b!79<H5#6gXa@&>|oWmL*>TuDX98Ln6(%cIiQQ}O;ZJiFVz~Q5B7Bq5(Sq5@PiL1CdE-|F&pho78Hb%SFS}*2qH%<yh7R|mujS*vs9KR8r+f+2h`<A$ic;`a_OD+eg?-|x{X}vV4R$yXR+GVcO%^fXfvtdDU^4PM0^tHG%9qgS7ej=)=A0&QXt||R>+`a$X>9@~8`ab-&KAvm{6MbV)EX4a|7o6T}+{BY=8ZmvuOM{k)F-v&2743jCjkpB!kZ}`~%Hi5mm2uj?V}!lN%~oCGzGepx*V;NBMZka<Ws==0ZTw+egsMs--ycJ8q3NEJ2VQK*t5{*QXnJ2Y?vu6<B~kbW&Q@sn0Lf{Hdn&e$tnfU<2arx$+(f!%N3VDB(JJKmjvH2oA@mz4c$BE6X)})erGVfw_Ze}1m3f~D9WS@(#f|TMf~9Qa<pSj}t#O=I=;(#QjU_o4u+TVOr+7@waZg&AvU0AQKsh-!rAsP#)mgF;Q8c(v1DBr)C*9F+Q~<J(-6%iFpw9xJx10CUoBvWXh-n`w`ce~eFIko-?P&=04dhrb%Q|$n9)`GaAgNHa6npKZ#M63RWySn;1tW!8Dm|^xg>gBEt+-P(5mHm%@Zuljr*Gc$i>;qX79Th0quZebMxqs&oOQ?e^4bPVD$-y%M`i-5wsdUe1AXB`sfCtFh-~vR2E49-3~5|817C%JaX`SJ76U`$_E^Af%o6RIJ*KKty4Gf|<dRqRD^!h5uOt(q5bQaQvqu!;bZd}^tCD&g)SYK`I*eoiVn!u(iWxfsUo(lTx?B;@r*?mVM-y<sATe_k7pR)TQ@6Jrne0+?z8Z91yivJBO#sm}42Hx~AZvDEj>BGnn|AhS<2#&+*29Q%k9q48^b!J3gaO6bhQOq?abILExyI>|$88O*7}U(PnqlY|_E*NOHhd-5ys@op?;=AW>vBTwL70}f%M_`;JI5522{41Foued|^NbX?Wv9FXK;nXnnqwe#c4eF7M9dbUzlz5Q@3;kwkp>}6!-unT|87S5`u1N8`}JR*gLpoC5^okoW_4;(@V~O6CA}cO!WS$9>bp$<mLEHs57I``O2`FyH&!N#p($iBw$fmrXcCP}B-zG_Ns7b43Mk{l5ZyDHa_f~wc}_}s3t?QkqU8XLhNt%em~*$_IbbM8F~5S4mJfrx1={2Qc*rSnJqIi^H^>sWeEm8gvSKA5sb>sGvJ$u3<N<)BFIUT*CRWMChI=N&yOs)qM2L<C0TCrb0Q5SyxJ7LN)QM*W4IF$dYGgX#8iJPNU`AuqR!U06d(2iTE2f(7XjdN5)(e9vROL={jdChPu0;8KcIg$SdKO@N8p+dDtD7wVb>$I9B^=vTr(M{%IM1gk0m=?HOCIJrAh(o(P;FyJuHEXU(KHMwm~g)7sn*!uC>h$>@eS@P_FG4r&@wXa-*fa1rnsATZ%>WC&q40a9{C87GXlxw8CPIM7n8}_z04@(9HpH)*&%1Ajbkm*;lknA*2!~lIh7*t0LzV<f3O<pz|+=D+Ht_`F|eOwv>9}B3ymBHtIn6&<yoBR`&PPejs*>h?%y#NwXrnCSiZD2$CwbXw^{{=R@>nqT90?#OTZxa64#6OT%wFNZ;c_S)FI9|3f@ax@JMr0+$chXAdS<il&U^vvS)&<`;WdDxV&4W^y-`|Tx(JEMD5<=QuVddikqfso|~y3#|%cxT7oVMPTai6jzKJOk97y~VFjY!4&20?hCpeRExUnD^tf7p`YP9&=><IOM$l>s;Xa_H6miMMX=ycBu8d8D41j!C%dzC4A4(pi*Vs>vg6+n;?~14<cPEC>qEUy$mB)_tFeI0?XPY$!?C?(2tK4fkiBI|ZLKelKALH)0_32aG)fV>r^tX8T51;N%Z1Xk}_TOU>{_J%9_Ms25GAq@mX9!9~>e@ZtBx%&#k;OF>s*w5G4tE{Np$$Oe@~NE|fEMSyURs(Btgaw1Ew$+Gi?d&yGv>Kw6C`A0=b&zI&-)in++ww-v9!x<col7vC<XaaVyCm82KVKa7U)MA@XE5`m)jQ~N)PgR7VQx4RUvq7bZFIr++e{!V)MRwF`*Sl!yNAJBhFRwf*$MmL!HsN|5Vf7jExtX_2RxCBtZ43us7~;*}FhUloFS_k7xiJR$IyS&{)Q`9kK~UrxlhU=*{$&d)!6}rd<KVpdYSd42y~3X)k<O*S2HN+H#aA$g`XDMjXA-z?VU4hICpfM%2%#<}sySM$fb+#gy6wP7Ovk>!Ho+aMNF0UK5U;seuMSpi<mC6D17crKL&SqPdqxHE}+j#5YbmGGTO_TD{%eS2M&%EczHpj9ETh5bKQeA-TAhilF7Vej1K+x>AN{oRh@fSq>^Us&ylmaRV20ih%;VO`-yS1__kZinvEjNnK0(;+UOQz$`mRx;))xFXNNf5lD|RZ(cF_b81}Tl97(%+VjC%IiIFb#3sw3WVaoTkB7!y%1NC?q4gxVR*63JY#t4`(I9Q71H6`+*j(V5f`vqair$uIu;)wR=%x6{JA=?b!jYBC!kwUBXN7x_rxp#nQzkP1q0i=cJG~0eRx8Ei^_r3HZPt{WM~)+a5<@J2$feI5-Gw>pj8I5@QZ(Pt3mEfdy!FQMeQ{kEyGn^hZCFT<u6j?iuAxG)KQ-Kr_Yd)5NLpWQO3Yo@lG2I-8^e+%1HBqKN<=ieojOD3P>zeu9jb^0a$=MyxW3NN^TY4&eSG}qjZF0GAlq-obG;pR@7~z>ZG7eS50cRZ=v-^JhCEP9XGmb?ffuKuQ7IVnnxaDMQ0vwCa2+J@Qe%6p)tC?-HQ_lX-f!vNYA#^*F`^k?j9oB9Jp}43brPtS>}xsvnc1F3MISffe}CLHbktIc1Jbxmad7PeK^kYloxm)YLAG>_F*Jut*ro@UOf&9ufU4dd4}vgf^BzT=RRx4!iKBv~kJC2w+#ss8yTmk)R!rxOw!IlVA2;Zw__-=0lgAx;af?Eq0Mop!^|3%fk%~{ROezQbJY1<rJ8t%_Gw$H*O#r~n!`-QXj7HrL33Sr{Pg0MoNaDZ?bXB3rKzrGr$%Z##=Jgi6bn0*PDY-V}C61dC#N*a^6#&B+ySc;u!w&_sEuZsy)r_@3SR-|BIDQpDMgmVLs-T}KMpf2X49mwPMMTo+`lUG9Uz@KaPwxg^?ryxr-|5!tUA{ej3Nr#le*1_geL04@_W=)LXpQUSVY&`7qc!#~Vxn<x)=w9u*{D3@DDzNmcdQ^InQ`0AXsbro6rfWE*ggno1(|IL8f?td*d=^eK|U)!VjC-Q4y>go+wf^PdWA)=n$=MzX!p{jam>`?{G@{&#+AAy$W^W$mu(+*G^re#`{Qo30YlJcwnd@wPnWB=osB>rkk-?Qea0Z_20Xxu&Q5K{DEG3TVBedu^gBj<@WDSk#7|O%nV`1!);NArjk&VX<{}7uXr6}HJe23@q2n715RV!Z9-M}8l+wD{l+(>QY7^X)r-4IY#RSQShQ++#Nj&<tXSCvtXnL(pFT>KgxK5}fhg2$v$Xc2bq+*_V$HhOD+L}8Z&ReS<wv_7#vE^}T=>$m1M(X$3W}GJ0tu^yJ?U7`ThNqY^(DBI{hy3%bJ@;`7-#>@HPP_kUwy!m$$7lUexBCVoN}8$xz&x&6W026<qOH4{ED#>!cD%`h53^t)SGD$)k#$Ou=?xSL`pUHq-LWWr#~4_EMvF0{5KkKYLZ^F#q9*9c_PWszFR<RFCEq*pb<A_nK9x@?1VL9hH3sCxY+|K$$U%IVR3IFsB2mTXJ4MNN2R$#)0Ja+B0JWGp5d$bEysv8;9+vd(Hs-K?B~5z5c=N|%_{T%ej~p}RI3P<qUUT@yOCu9_i)%{a8uS@m^8J8}6`*;zPOvLjKh*u`U{=v5SoY9_b*LE`JV9F3J*LWO#|;)+JvwJ&tC@YwryB2t;PBSD<({&`GSox-Y0tK@#r@1RWxPGIfyaD^dbod94kPu$S`xKAH6<<ruiG$aYVh(pa}EToNMxW*QKnIMo(-gypu2Jf+k|2N*Z&8!lC;+"


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _git_blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def _identity_ok(identity: Mapping[str, object], raw: bytes) -> bool:
    return (
        {"path", "git_blob_sha1", "size_bytes", "raw_sha256"} <= set(identity)
        and type(identity["path"]) is str
        and type(identity["git_blob_sha1"]) is str
        and type(identity["size_bytes"]) is int
        and type(identity["raw_sha256"]) is str
        and len(raw) == identity["size_bytes"]
        and _git_blob(raw) == identity["git_blob_sha1"]
        and _sha256(raw) == identity["raw_sha256"]
    )


def _identity_dicts(value: object) -> Iterable[dict[str, object]]:
    if type(value) is dict:
        if {"path", "git_blob_sha1", "size_bytes", "raw_sha256"} <= set(value):
            yield value
        for nested in value.values():
            yield from _identity_dicts(nested)
    elif type(value) is list:
        for nested in value:
            yield from _identity_dicts(nested)


def verify_identity_graph(roots: Iterable[dict[str, object]], read_blob: Callable[[str], bytes], expected: int) -> tuple[dict[str, object], ...]:
    """Recursively verify an exact identity graph without checkout reads."""
    pending = list(roots)
    verified: dict[str, dict[str, object]] = {}
    while pending:
        identity = pending.pop(0)
        path = identity.get("path")
        if type(path) is not str or path in verified:
            continue
        raw = read_blob(str(identity.get("git_blob_sha1")))
        if not _identity_ok(identity, raw):
            raise PermissionError(f"H27 predecessor identity mismatch: {path}.")
        verified[path] = identity
        try:
            parsed = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
        pending.extend(_identity_dicts(parsed))
    if len(verified) != expected:
        raise PermissionError(f"H27 requires exactly {expected} unique predecessor identities, got {len(verified)}.")
    return tuple(verified.values())


def bound_predecessor_identities() -> tuple[dict[str, object], ...]:
    try:
        value = json.loads(zlib.decompress(base64.b85decode(_IDENTITY_GRAPH_B85)).decode("ascii"))
    except (ValueError, UnicodeDecodeError, zlib.error, json.JSONDecodeError) as exc:
        raise PermissionError("H27 embedded predecessor identity manifest invalid.") from exc
    if type(value) is not list or len(value) != 130 or any(type(item) is not dict for item in value):
        raise PermissionError("H27 embedded predecessor identity count or type invalid.")
    if len({item.get("path") for item in value}) != 130:
        raise PermissionError("H27 embedded predecessor identities are not unique.")
    return tuple(value)


def verify_bound_predecessors(read_blob: Callable[[str], bytes]) -> None:
    for identity in bound_predecessor_identities():
        raw = read_blob(str(identity.get("git_blob_sha1")))
        if not _identity_ok(identity, raw):
            raise PermissionError(f"H27 predecessor identity mismatch: {identity.get('path')}.")


def canonical_registry_record(*, transition_index: int, state: str, prior_record_raw_sha256: Optional[str], creator_sha256: str, bundle_sha256: Optional[str], failure_stage: Optional[str]) -> bytes:
    if type(transition_index) is not int or transition_index not in (0, 1, 2):
        raise TypeError("H27 transition_index must be an exact bounded integer.")
    if state not in ("reserved", "consumed", "bundle_creation_succeeded", "terminal_failure"):
        raise ValueError("H27 registry state invalid.")
    for value in (creator_sha256,):
        if type(value) is not str or re.fullmatch(r"[0-9a-f]{64}", value) is None:
            raise ValueError("H27 registry digest invalid.")
    for value in (prior_record_raw_sha256, bundle_sha256):
        if value is not None and (type(value) is not str or re.fullmatch(r"[0-9a-f]{64}", value) is None):
            raise ValueError("H27 optional registry digest invalid.")
    allowed_failure = (None, "after_reservation_before_consumption", "after_consumption_before_bundle_success")
    if failure_stage not in allowed_failure:
        raise ValueError("H27 failure stage invalid.")
    if state == "reserved" and not (transition_index == 0 and prior_record_raw_sha256 is None and bundle_sha256 is None and failure_stage is None):
        raise ValueError("H27 reserved transition invalid.")
    if state == "consumed" and not (transition_index == 1 and prior_record_raw_sha256 is not None and bundle_sha256 is None and failure_stage is None):
        raise ValueError("H27 consumed transition invalid.")
    if state == "bundle_creation_succeeded" and not (transition_index == 2 and prior_record_raw_sha256 is not None and bundle_sha256 is not None and failure_stage is None):
        raise ValueError("H27 success transition invalid.")
    if state == "terminal_failure" and not (transition_index in (1, 2) and prior_record_raw_sha256 is not None and bundle_sha256 is None and failure_stage is not None):
        raise ValueError("H27 failure transition invalid.")
    payload = {
        "schema_version": 1,
        "registry_namespace": REGISTRY_NAMESPACE,
        "creation_authority_artifact_id": AUTHORITY_ID,
        "transition_index": transition_index,
        "state": state,
        "prior_record_raw_sha256": prior_record_raw_sha256,
        "expected_execution_git_head": EXPECTED_EXECUTION_HEAD,
        "creator_implementation_raw_sha256": creator_sha256,
        "bundle_manifest_raw_sha256": bundle_sha256,
        "failure_stage": failure_stage,
    }
    prefix = (json.dumps(payload, ensure_ascii=False, allow_nan=False, separators=(",", ":")) + "\n").encode("utf-8")
    payload["record_id"] = _sha256(prefix)
    raw = (json.dumps(payload, ensure_ascii=False, allow_nan=False, separators=(",", ":")) + "\n").encode("utf-8")
    if tuple(payload) != RECORD_FIELDS:
        raise AssertionError("H27 registry record order drift.")
    return raw


def _read_blob(blob_sha1: str) -> bytes:
    if re.fullmatch(r"[0-9a-f]{40}", blob_sha1) is None:
        raise PermissionError("H27 Git blob identity malformed.")
    result = subprocess.run(
        ["git", f"--git-dir={GIT_DATABASE}", "cat-file", "blob", blob_sha1],
        check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        raise PermissionError("H27 exact Git blob unavailable.")
    return result.stdout


def _strict_json(raw: bytes) -> dict[str, object]:
    if raw.startswith(b"\xef\xbb\xbf") or b"\r" in raw or not raw.endswith(b"\n"):
        raise PermissionError("H27 canonical JSON bytes invalid.")
    value = json.loads(raw)
    if type(value) is not dict:
        raise PermissionError("H27 expected an exact JSON object.")
    return value


def _verify_source() -> str:
    if Path(__file__).resolve(strict=True) != SOURCE_ENTRYPOINT:
        raise PermissionError("H27 creator must execute only from the immutable administrative source.")
    raw = SOURCE_ENTRYPOINT.read_bytes()
    manifest_raw = SOURCE_MANIFEST.read_bytes()
    manifest = _strict_json(manifest_raw)
    if tuple(manifest) != ("schema_version", "source_id", "reviewed_creator_contract_identity", "reviewed_creator_binding_identity", "root", "entrypoint"):
        raise PermissionError("H27 creator source manifest order mismatch.")
    if manifest["schema_version"] != 1 or manifest["source_id"] != "H27_REVIEWED_CONTROL_BUNDLE_CREATOR_IMPLEMENTATION_SOURCE_V1" or manifest["root"] != str(SOURCE_ROOT):
        raise PermissionError("H27 creator source manifest values mismatch.")
    if manifest["reviewed_creator_contract_identity"] != {"git_blob_sha1":"cee37fbececa8387266ba693ae915aeb8ce3ac4e","size_bytes":9920,"raw_sha256":"8decca47ec6947951fddfb8becdaa550609fa50e2c12e310d7a4476210f583da"}:
        raise PermissionError("H27 reviewed creator contract identity mismatch.")
    if manifest["reviewed_creator_binding_identity"] != {"git_blob_sha1":"b5ec9c1c65e1f15a8eff65fec7749d808c1193ae","size_bytes":3248,"raw_sha256":"54a31600aa1898d946b57bcda5330993e6740a642aec5f1a7ca35d5bb96b380c"}:
        raise PermissionError("H27 reviewed creator binding identity mismatch.")
    entrypoint = manifest["entrypoint"]
    if type(entrypoint) is not dict or tuple(entrypoint) != ("path", "git_blob_sha1", "size_bytes", "raw_sha256"):
        raise PermissionError("H27 creator entrypoint identity schema mismatch.")
    if entrypoint["path"] != SOURCE_ENTRYPOINT.name or not _identity_ok(entrypoint, raw):
        raise PermissionError("H27 creator entrypoint identity mismatch.")
    return _sha256(raw)


def _require_exact_environment() -> None:
    if sys.platform != "darwin" or fcntl is None or os.environ.get(ACK_ENV) != "1" or len(sys.argv) != 1:
        raise PermissionError("H27 creator requires exact macOS acknowledgement and no arguments.")
    if TARGET_CHECKOUT.resolve(strict=True) != TARGET_CHECKOUT or GIT_DATABASE.resolve(strict=True) != GIT_DATABASE:
        raise PermissionError("H27 target checkout or Git database realpath mismatch.")
    head = subprocess.run(["git", "-C", str(TARGET_CHECKOUT), "rev-parse", "HEAD"], check=True, text=True, stdout=subprocess.PIPE).stdout.strip()
    status = subprocess.run(["git", "-C", str(TARGET_CHECKOUT), "status", "--porcelain"], check=True, text=True, stdout=subprocess.PIPE).stdout
    if head != EXPECTED_EXECUTION_HEAD or status:
        raise PermissionError("H27 target checkout HEAD or cleanliness mismatch.")


def _validate_registry_locked(handle) -> None:
    handle.seek(0)
    raw = handle.read()
    if raw and not raw.endswith(b"\n"):
        raise PermissionError("H27 registry has a partial final line.")
    for line in raw.splitlines(keepends=True):
        record = _strict_json(line)
        if tuple(record) != RECORD_FIELDS:
            raise PermissionError("H27 registry record schema/order mismatch.")
        if record["creation_authority_artifact_id"] == AUTHORITY_ID:
            raise PermissionError("H27 authority ID is permanently non-reusable.")


def _append_fsync(handle, raw: bytes) -> None:
    handle.seek(0, os.SEEK_END)
    handle.write(raw)
    handle.flush()
    os.fsync(handle.fileno())


def _bundle_bytes() -> dict[str, bytes]:
    result: dict[str, bytes] = {}
    for identity in BUNDLE_FILES:
        raw = _read_blob(identity["git_blob_sha1"])
        if not _identity_ok(identity, raw):
            raise PermissionError(f"H27 bundle source mismatch: {identity['path']}.")
        relative = PurePosixPath(identity["path"])
        if relative.is_absolute() or ".." in relative.parts or str(relative) in result:
            raise PermissionError("H27 bundle relative path invalid.")
        result[str(relative)] = raw
    if len(result) != 6:
        raise PermissionError("H27 bundle requires exactly six files.")
    return result


def _closed_bundle_digest(root: Path) -> str:
    actual = sorted(str(path.relative_to(root).as_posix()) for path in root.rglob("*") if path.is_file())
    expected = sorted(identity["path"] for identity in BUNDLE_FILES)
    if actual != expected:
        raise PermissionError("H27 closed bundle path set mismatch.")
    lines = []
    for identity in BUNDLE_FILES:
        raw = (root / identity["path"]).read_bytes()
        if not _identity_ok(identity, raw):
            raise PermissionError("H27 closed bundle file mismatch.")
        lines.append(f"{identity['path']}\0{identity['git_blob_sha1']}\0{identity['size_bytes']}\0{identity['raw_sha256']}\n")
    return _sha256("".join(lines).encode("utf-8"))


def _fsync_dir(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _publish_bundle(files: Mapping[str, bytes]) -> str:
    if CONTROL_PARENT.resolve(strict=True) != CONTROL_PARENT or CONTROL_PARENT.is_symlink():
        raise PermissionError("H27 control parent realpath mismatch.")
    for path in (FINAL_BUNDLE, STAGING_BUNDLE):
        try:
            os.lstat(path)
        except FileNotFoundError:
            pass
        else:
            raise FileExistsError("H27 final or staging bundle already exists.")
    STAGING_BUNDLE.mkdir(mode=0o700)
    for relative, raw in files.items():
        destination = STAGING_BUNDLE / relative
        destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        fd = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o400)
        try:
            with os.fdopen(fd, "wb", closefd=False) as stream:
                stream.write(raw)
                stream.flush()
            os.fsync(fd)
        finally:
            os.close(fd)
    for directory in sorted({path.parent for path in STAGING_BUNDLE.rglob("*")}, key=lambda p: len(p.parts), reverse=True):
        _fsync_dir(directory)
    staged_digest = _closed_bundle_digest(STAGING_BUNDLE)
    libc = ctypes.CDLL(None, use_errno=True)
    renameatx_np = libc.renameatx_np
    renameatx_np.argtypes = (ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint)
    renameatx_np.restype = ctypes.c_int
    if renameatx_np(AT_FDCWD, os.fsencode(STAGING_BUNDLE), AT_FDCWD, os.fsencode(FINAL_BUNDLE), RENAME_EXCL) != 0:
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error), str(FINAL_BUNDLE))
    _fsync_dir(CONTROL_PARENT)
    if _closed_bundle_digest(FINAL_BUNDLE) != staged_digest:
        raise PermissionError("H27 final bundle digest mismatch.")
    return staged_digest


def execute_reviewed_control_bundle_creator() -> str:
    """Consume the exact authority and publish the exact bundle once."""
    creator_sha = _verify_source()
    _require_exact_environment()
    verify_bound_predecessors(_read_blob)
    authority = _strict_json(_read_blob(CREATOR_ROOTS[0]["git_blob_sha1"]))
    if authority.get("creation_authority_artifact_id") != AUTHORITY_ID or authority.get("expected_execution_git_head") != EXPECTED_EXECUTION_HEAD or authority.get("single_use") is not True or authority.get("consumed") is not False:
        raise PermissionError("H27 creation authority artifact mismatch.")
    files = _bundle_bytes()
    if REGISTRY.parent.resolve(strict=True) != REGISTRY.parent or not REGISTRY.is_file() or REGISTRY.is_symlink():
        raise PermissionError("H27 exact pre-existing registry required.")
    with REGISTRY.open("r+b", buffering=0) as registry:
        fcntl.flock(registry.fileno(), fcntl.LOCK_EX)
        _validate_registry_locked(registry)
        reserved = canonical_registry_record(transition_index=0, state="reserved", prior_record_raw_sha256=None, creator_sha256=creator_sha, bundle_sha256=None, failure_stage=None)
        _append_fsync(registry, reserved)
        consumed = None
        try:
            pending_consumed = canonical_registry_record(transition_index=1, state="consumed", prior_record_raw_sha256=_sha256(reserved), creator_sha256=creator_sha, bundle_sha256=None, failure_stage=None)
            _append_fsync(registry, pending_consumed)
            consumed = pending_consumed
            bundle_sha = _publish_bundle(files)
            success = canonical_registry_record(transition_index=2, state="bundle_creation_succeeded", prior_record_raw_sha256=_sha256(consumed), creator_sha256=creator_sha, bundle_sha256=bundle_sha, failure_stage=None)
            _append_fsync(registry, success)
            return bundle_sha
        except BaseException:
            prior = consumed if consumed is not None else reserved
            stage = "after_consumption_before_bundle_success" if consumed is not None else "after_reservation_before_consumption"
            failure = canonical_registry_record(transition_index=2 if consumed is not None else 1, state="terminal_failure", prior_record_raw_sha256=_sha256(prior), creator_sha256=creator_sha, bundle_sha256=None, failure_stage=stage)
            _append_fsync(registry, failure)
            raise
        finally:
            fcntl.flock(registry.fileno(), fcntl.LOCK_UN)


def main() -> int:
    execute_reviewed_control_bundle_creator()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
