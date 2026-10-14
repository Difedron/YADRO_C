#!/usr/bin/env python3
import csv
import hashlib
import json
import os
import random
import shutil
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent / "yadro_120_tests"
CASES = ROOT / "cases"
ENDIAN = "<" if sys.byteorder == "little" else ">"


def norm(s: int) -> int:
    if s > 255:
        return s % 251
    if s < 0:
        return (-s) % 241
    return s


def oracle(h, w, pixels, kh, kw, kernel):
    out = bytearray(3 * h * w)
    cy, cx = kh // 2, kw // 2
    for y in range(h):
        for x in range(w):
            sums = [0, 0, 0]
            for ky in range(kh):
                sy = y + ky - cy
                if sy < 0 or sy >= h:
                    continue
                for kx in range(kw):
                    sx = x + kx - cx
                    if sx < 0 or sx >= w:
                        continue
                    d = kernel[ky * kw + kx]
                    base = 3 * (sy * w + sx)
                    sums[0] += d * pixels[base]
                    sums[1] += d * pixels[base + 1]
                    sums[2] += d * pixels[base + 2]
            base = 3 * (y * w + x)
            out[base:base+3] = bytes(norm(s) for s in sums)
    return bytes(out)


def pack_valid(h, w, pixels, kh, kw, kernel):
    assert len(pixels) == 3 * h * w
    assert len(kernel) == kh * kw
    assert kh > 0 and kw > 0 and kh % 2 == 1 and kw % 2 == 1
    data = bytearray()
    data += struct.pack(ENDIAN + "II", h, w)
    data += bytes(pixels)
    data += struct.pack(ENDIAN + "HH", kh, kw)
    data += struct.pack(f"{len(kernel)}b", *kernel)
    expected = bytearray()
    expected += struct.pack(ENDIAN + "II", h, w)
    expected += oracle(h, w, pixels, kh, kw, kernel)
    return bytes(data), bytes(expected)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def pix_const(h, w, a, b=None, c=None):
    if b is None: b = a
    if c is None: c = a
    return [v for _ in range(h*w) for v in (a, b, c)]


def pix_pattern(h, w, fn):
    p = []
    for y in range(h):
        for x in range(w):
            vals = fn(y, x)
            p.extend(int(v) & 0xFF for v in vals)
    return p


def add_valid(cases, name, desc, h, w, pixels, kh, kw, kernel):
    data, out = pack_valid(h, w, pixels, kh, kw, kernel)
    cases.append({
        "kind": "valid", "name": name, "description": desc,
        "input": data, "output": out, "expected_rc": 0,
        "h": h, "w": w, "kh": kh, "kw": kw,
    })


def add_invalid(cases, name, desc, data):
    cases.append({
        "kind": "invalid_input", "name": name, "description": desc,
        "input": data, "output": None, "expected_rc": 1,
    })


def build_cases():
    C = []
    # 001-020: basics / degenerate valid dimensions
    add_valid(C,"001_scalar_zero","1x1, zero pixel, identity kernel",1,1,[0,0,0],1,1,[1])
    add_valid(C,"002_scalar_255","1x1, all channels 255, identity kernel",1,1,[255,255,255],1,1,[1])
    add_valid(C,"003_scalar_negative","1x1, signed -1 kernel",1,1,[1,2,255],1,1,[-1])
    add_valid(C,"004_scalar_min_coeff","1x1, D=-128",1,1,[255,127,1],1,1,[-128])
    add_valid(C,"005_scalar_max_coeff","1x1, D=127",1,1,[255,254,253],1,1,[127])
    add_valid(C,"006_scalar_zero_kernel","1x1, D=0",1,1,[200,111,17],1,1,[0])
    add_valid(C,"007_zero_both_dims","H=0,W=0, valid kernel still present",0,0,[],1,1,[1])
    add_valid(C,"008_zero_height","H=0,W=5, 3x3 kernel",0,5,[],3,3,[1,-1,2,-2,3,-3,4,-4,5])
    add_valid(C,"009_zero_width","H=5,W=0, 1x3 kernel",5,0,[],1,3,[-128,0,127])
    add_valid(C,"010_one_by_two","1x2 identity",1,2,[1,2,3,250,251,255],1,1,[1])
    add_valid(C,"011_two_by_one","2x1 identity",2,1,[0,1,2,253,254,255],1,1,[1])
    add_valid(C,"012_one_by_five","1x5 identity ramp",1,5,pix_pattern(1,5,lambda y,x:(x,100+x,200+x)),1,1,[1])
    add_valid(C,"013_five_by_one","5x1 identity ramp",5,1,pix_pattern(5,1,lambda y,x:(y,50+y,250-y)),1,1,[1])
    add_valid(C,"014_two_by_two","2x2 identity",2,2,pix_pattern(2,2,lambda y,x:(y*2+x,100+y*2+x,200+y*2+x)),1,1,[1])
    add_valid(C,"015_three_by_three","3x3 identity",3,3,pix_pattern(3,3,lambda y,x:((y*3+x)*7%256,(y*3+x)*13%256,(y*3+x)*29%256)),1,1,[1])
    add_valid(C,"016_rect_identity","4x7 identity, varied channels",4,7,pix_pattern(4,7,lambda y,x:((y*17+x*3)%256,(y*5+x*19)%256,(255-y*7-x*11)%256)),1,1,[1])
    add_valid(C,"017_mixed_channels","2x3 independent A/B/C",2,3,[1,101,201,2,102,202,3,103,203,4,104,204,5,105,205,6,106,206],1,1,[1])
    add_valid(C,"018_all_max","3x2 all 255",3,2,pix_const(3,2,255),1,1,[1])
    add_valid(C,"019_checker","3x4 checkerboard channels",3,4,pix_pattern(3,4,lambda y,x:((255 if (x+y)%2 else 0),(17 if x%2 else 239),(y*80+x*9)%256)),1,1,[1])
    add_valid(C,"020_channel_ramps","7x6 three distinct ramps",7,6,pix_pattern(7,6,lambda y,x:((y*6+x)%256,(200-y*6-x)%256,(x*31+y*7)%256)),1,1,[1])

    # 021-045: padding, kernel geometry, no-flip detection
    add_valid(C,"021_1x1_k3","1x1 with 3x3 kernel, only center contributes",1,1,[7,11,13],3,3,[1,2,3,4,5,6,7,8,9])
    add_valid(C,"022_1x1_k5_asym","1x1 with asymmetric 5x5 kernel",1,1,[250,128,3],5,5,list(range(-12,13)))
    add_valid(C,"023_row_k1x3","1x4 with 1x3 kernel",1,4,pix_pattern(1,4,lambda y,x:(10+x,40+x*2,200-x)),1,3,[-3,5,7])
    add_valid(C,"024_row_kernel_larger","1x4 with 1x7 kernel larger than row",1,4,pix_pattern(1,4,lambda y,x:(x*60,255-x*40,30+x)),1,7,[-3,-2,-1,5,7,11,13])
    add_valid(C,"025_col_k3x1","4x1 with 3x1 kernel",4,1,pix_pattern(4,1,lambda y,x:(20+y,100-y*3,200-y*5)),3,1,[-7,2,9])
    add_valid(C,"026_col_kernel_larger","4x1 with 7x1 kernel larger than column",4,1,pix_pattern(4,1,lambda y,x:(50*y,7+y,255-20*y)),7,1,[-9,-5,-1,3,7,11,15])
    add_valid(C,"027_2x2_k3","2x2 with 3x3 all-ones padding",2,2,pix_pattern(2,2,lambda y,x:(1+y*2+x,11+y*2+x,21+y*2+x)),3,3,[1]*9)
    add_valid(C,"028_2x3_k5x3","kernel taller than image",2,3,pix_pattern(2,3,lambda y,x:(10+y*20+x,80+y+x*3,200-y*7-x)),5,3,[i-7 for i in range(15)])
    add_valid(C,"029_3x2_k3x5","kernel wider than image",3,2,pix_pattern(3,2,lambda y,x:(3+y*8+x,130-y*5-x,240-y*9+x)),3,5,[7-i for i in range(15)])
    add_valid(C,"030_3x3_k5","5x5 kernel larger both ways",3,3,pix_pattern(3,3,lambda y,x:(y*30+x*4,255-y*20-x*5,90+y*7+x*11)),5,5,[((i*7)%17)-8 for i in range(25)])
    basepix = pix_pattern(4,5,lambda y,x:(1+y*5+x,61+y*5+x,121+y*5+x))
    for idx,(pos,label) in enumerate([((0,0),"tl"),((0,2),"tr"),((2,0),"bl"),((2,2),"br")], start=31):
        k=[0]*9; k[pos[0]*3+pos[1]]=1
        add_valid(C,f"{idx:03d}_kernel_impulse_{label}",f"3x3 kernel impulse {label}; detects accidental flip",4,5,basepix,3,3,k)
    add_valid(C,"035_asym_k3x3","asymmetric 3x3 signed kernel",4,4,pix_pattern(4,4,lambda y,x:(10+y*7+x*3,200-y*4-x*9,50+y*11+x)),3,3,[-4,-3,-2,-1,0,1,2,3,4])
    add_valid(C,"036_asym_k3x5","asymmetric 3x5 kernel",4,6,pix_pattern(4,6,lambda y,x:((y*41+x*17)%256,(y*13+x*29)%256,(y*23+x*31)%256)),3,5,[-8,-7,-6,-5,-4,-3,-2,-1,0,1,2,3,4,5,6])
    add_valid(C,"037_asym_k5x3","asymmetric 5x3 kernel",6,4,pix_pattern(6,4,lambda y,x:((y*19+x*37)%256,(255-y*11-x*7)%256,(y*5+x*53)%256)),5,3,[6,5,4,3,2,1,0,-1,-2,-3,-4,-5,-6,-7,-8])
    add_valid(C,"038_row_asym","1x7 asymmetric 1x5",1,7,pix_pattern(1,7,lambda y,x:(20*x,200-x*17,3+x*9)),1,5,[-11,-3,2,7,13])
    add_valid(C,"039_col_asym","7x1 asymmetric 5x1",7,1,pix_pattern(7,1,lambda y,x:(15*y,240-y*20,10+y*17)),5,1,[-13,-5,1,9,17])
    imp_corner = pix_const(5,5,0); imp_corner[0:3]=[255,128,1]
    add_valid(C,"040_image_impulse_corner","input impulse at top-left, 3x3 kernel",5,5,imp_corner,3,3,[1,2,3,4,5,6,7,8,9])
    imp_center = pix_const(5,5,0); bi=3*(2*5+2); imp_center[bi:bi+3]=[255,128,1]
    add_valid(C,"041_image_impulse_center","input impulse at center, no-flip detector",5,5,imp_center,3,3,[1,2,3,4,5,6,7,8,9])
    edge_h = pix_const(3,6,0)
    for x in range(6): edge_h[3*x:3*x+3]=[x*30,255-x*20,10+x]
    add_valid(C,"042_top_edge_signal","nonzero top edge exercises vertical padding",3,6,edge_h,5,3,[i-7 for i in range(15)])
    edge_v = pix_const(6,3,0)
    for y in range(6):
        b=3*(y*3); edge_v[b:b+3]=[y*35,200-y*20,5+y]
    add_valid(C,"043_left_edge_signal","nonzero left edge exercises horizontal padding",6,3,edge_v,3,5,[7-i for i in range(15)])
    add_valid(C,"044_kernel_7x9_gt_image","7x9 kernel on 3x4 image",3,4,pix_pattern(3,4,lambda y,x:(y*40+x*9,180-y*17-x*3,250-y*13-x*11)),7,9,[((i*5)%23)-11 for i in range(63)])
    add_valid(C,"045_kernel_11x13_gt_2x2","11x13 kernel on 2x2 image",2,2,pix_pattern(2,2,lambda y,x:(50+y*60+x*20,10+y*40+x*70,255-y*80-x*30)),11,13,[((i*11)%31)-15 for i in range(143)])

    # 046-075: arithmetic / modulo / signedness boundaries
    scalar_targets=[
        (46,"sum_0",0,1),(47,"sum_1",1,1),(48,"sum_240",240,1),(49,"sum_241",241,1),
        (50,"sum_250",250,1),(51,"sum_251",251,1),(52,"sum_255",255,1),
        (53,"sum_neg1",1,-1),(54,"sum_neg240",240,-1),(55,"sum_neg241",241,-1),(56,"sum_neg242",242,-1),
    ]
    for num,label,p,d in scalar_targets:
        add_valid(C,f"{num:03d}_{label}",f"exact scalar arithmetic boundary: {label}",1,1,[p,p,p],1,1,[d])
    # exact 256/257 using center+right contributions at x=0 of width 2
    add_valid(C,"057_sum_256","two positive contributions can cross 255 to exactly 256",1,2,[128,128,128,128,128,128],1,3,[0,1,1])
    add_valid(C,"058_sum_257","exact 257 at left output",1,2,[128,128,128,129,129,129],1,3,[0,1,1])
    add_valid(C,"059_sum_501","250+251 positive accumulation",1,2,[250,250,250,251,251,251],1,3,[0,1,1])
    add_valid(C,"060_sum_502_mod0","502 % 251 == 0",1,2,[251,251,251,251,251,251],1,3,[0,1,1])
    add_valid(C,"061_sum_503_mod1","503 % 251 == 1",1,2,[251,251,251,252,252,252],1,3,[0,1,1])
    add_valid(C,"062_neg482_mod0","-482 => 482 % 241 == 0",1,2,[241,241,241,241,241,241],1,3,[0,-1,-1])
    add_valid(C,"063_neg483_mod1","-483 => 483 % 241 == 1",1,2,[241,241,241,242,242,242],1,3,[0,-1,-1])
    add_valid(C,"064_max_positive_product","255*127 single-product extreme",1,1,[255,255,255],1,1,[127])
    add_valid(C,"065_max_negative_product","255*(-128) single-product extreme",1,1,[255,255,255],1,1,[-128])
    add_valid(C,"066_cancel_zero","100-200+100 = 0 at center",1,3,pix_const(1,3,0),1,3,[1,-1,1])
    # overwrite data for exact cancellation cases
    C[-1]["input"], C[-1]["output"] = pack_valid(1,3,[100,100,100,200,200,200,100,100,100],1,3,[1,-1,1])
    add_valid(C,"067_cancel_plus1","100-199+100 = 1",1,3,[100]*3+[199]*3+[100]*3,1,3,[1,-1,1])
    add_valid(C,"068_cancel_minus1","100-201+100 = -1",1,3,[100]*3+[201]*3+[100]*3,1,3,[1,-1,1])
    add_valid(C,"069_extreme_coeff_mix","kernel includes both -128 and 127",2,3,pix_pattern(2,3,lambda y,x:(255-x*20-y*30,1+x+y,128+y*10+x*5)),3,3,[-128,127,-128,127,0,127,-128,127,-128])
    add_valid(C,"070_all255_all127","3x3 all-255 image, all +127 kernel",3,3,pix_const(3,3,255),3,3,[127]*9)
    add_valid(C,"071_all255_allneg128","3x3 all-255 image, all -128 kernel",3,3,pix_const(3,3,255),3,3,[-128]*9)
    add_valid(C,"072_alternating_kernel_signs","alternating signed kernel",5,5,pix_const(5,5,255,127,1),5,5,[127 if i%2==0 else -128 for i in range(25)])
    add_valid(C,"073_alternating_pixels","0/255 alternating pixels with signed kernel",5,6,pix_pattern(5,6,lambda y,x:((255 if (x+y)%2 else 0),(0 if x%2 else 255),(255 if y%2 else 0))),3,5,[12,-17,23,-31,41,-53,67,-79,83,-97,101,-113,127,-128,1])
    add_valid(C,"074_channels_different_signs","same position yields positive/negative/zero-ish channel sums",1,3,[10,200,100,20,100,100,30,0,200],1,3,[-2,3,-4])
    add_valid(C,"075_channels_different_modulo","three channels deliberately cross modulo rules differently",2,2,[255,1,240, 254,2,241, 253,3,242, 252,4,243],3,3,[127,-128,127,-128,127,-128,127,-128,127])

    # 076-098: deterministic differential fuzz, including kernels larger than images.
    rng = random.Random(20261007)
    odd_choices=[1,3,5,7,9]
    for n in range(76,99):
        h=rng.randint(1,8); w=rng.randint(1,9)
        kh=rng.choice(odd_choices); kw=rng.choice(odd_choices)
        pixels=[rng.randrange(256) for _ in range(3*h*w)]
        kernel=[rng.randint(-128,127) for _ in range(kh*kw)]
        add_valid(C,f"{n:03d}_random_{h}x{w}_k{kh}x{kw}",
                  f"fixed-seed differential random case {n-75}; full signed coefficient range",
                  h,w,pixels,kh,kw,kernel)

    assert len(C) == 98, len(C)

    # 099-112: malformed binary inputs / validation paths
    add_invalid(C,"099_empty_file","empty file: cannot read H",b"")
    add_invalid(C,"100_truncated_H","only 1 byte of H",b"\x01")
    add_invalid(C,"101_only_H","H present, W missing",struct.pack(ENDIAN+"I",1))
    add_invalid(C,"102_truncated_W","H plus only 2 bytes of W",struct.pack(ENDIAN+"I",1)+b"\x02\x00")
    add_invalid(C,"103_truncated_pixels_1x1","H=W=1 but only 2/3 ABC bytes",struct.pack(ENDIAN+"II",1,1)+b"\x01\x02")
    add_invalid(C,"104_truncated_pixels_2x2","2x2 ABC block one byte short",struct.pack(ENDIAN+"II",2,2)+bytes(range(11)))
    # Full 1x1 ABC, then missing kernel fields
    prefix = struct.pack(ENDIAN+"II",1,1)+bytes([1,2,3])
    add_invalid(C,"105_missing_DH","matrix complete, DH absent",prefix)
    add_invalid(C,"106_missing_DW","DH present, DW absent",prefix+struct.pack(ENDIAN+"H",3))
    add_invalid(C,"107_truncated_D","3x3 D one byte short",prefix+struct.pack(ENDIAN+"HH",3,3)+struct.pack("8b",*range(8)))
    add_invalid(C,"108_zero_DH","DH=0 should be rejected",prefix+struct.pack(ENDIAN+"HH",0,1))
    add_invalid(C,"109_zero_DW","DW=0 should be rejected",prefix+struct.pack(ENDIAN+"HH",1,0))
    add_invalid(C,"110_even_DH","even DH should be rejected",prefix+struct.pack(ENDIAN+"HH",2,1))
    add_invalid(C,"111_even_DW","even DW should be rejected",prefix+struct.pack(ENDIAN+"HH",1,2))
    add_invalid(C,"112_size_overflow","H=W=UINT32_MAX triggers 3*H*W size overflow on 64-bit",struct.pack(ENDIAN+"II",0xffffffff,0xffffffff))

    assert len(C) == 112, len(C)

    # 113-120 are command-line/path cases, represented in manifest only.
    cli = [
        ("113_cli_no_args","no arguments => 10","no_args",10),
        ("114_cli_only_i","only -i with valid filename => 10","only_i",10),
        ("115_cli_only_o","only -o with filename => 10","only_o",10),
        ("116_cli_flag_as_name","-i immediately followed by -o => 10","flag_as_name",10),
        ("117_missing_input_path","both flags but input file does not exist => EXIT_FAILURE","missing_input",1),
        ("118_missing_output_dir","output parent directory does not exist => EXIT_FAILURE","missing_output_dir",1),
        ("119_leading_dash_filenames","filenames beginning with '-' but not equal to flags are accepted","leading_dash",0),
        ("120_same_input_output","input and output may be same path because output opens after read/compute","same_path",0),
    ]
    for name,desc,mode,rc in cli:
        C.append({"kind":"cli","name":name,"description":desc,"mode":mode,"expected_rc":rc})

    assert len(C)==120, len(C)
    return C


def main():
    if ROOT.exists(): shutil.rmtree(ROOT)
    CASES.mkdir(parents=True)
    cases=build_cases()
    manifest=[]
    for i,c in enumerate(cases,1):
        assert int(c["name"].split("_")[0]) == i
        entry={k:v for k,v in c.items() if k not in ("input","output")}
        if c["kind"] in ("valid","invalid_input"):
            inp_name=c["name"]+".in"
            (CASES/inp_name).write_bytes(c["input"])
            entry["input_file"]="cases/"+inp_name
            entry["input_sha256"]=sha256(c["input"])
            if c["kind"]=="valid":
                out_name=c["name"]+".out"
                (CASES/out_name).write_bytes(c["output"])
                entry["output_file"]="cases/"+out_name
                entry["output_sha256"]=sha256(c["output"])
        manifest.append(entry)
    (ROOT/"manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
    with (ROOT/"manifest.csv").open("w",newline="",encoding="utf-8") as f:
        fields=["id","name","kind","description","expected_rc","h","w","kh","kw","input_file","output_file"]
        wr=csv.DictWriter(f,fieldnames=fields); wr.writeheader()
        for i,e in enumerate(manifest,1):
            wr.writerow({"id":i,**{k:e.get(k,"") for k in fields if k!="id"}})

    runner = r'''#!/usr/bin/env python3
import json, os, shutil, subprocess, sys, tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parent
MANIFEST=json.loads((ROOT/"manifest.json").read_text(encoding="utf-8"))
TIMEOUT=60

def run(cmd,cwd=None):
    try:
        return subprocess.run(cmd,cwd=cwd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=TIMEOUT)
    except subprocess.TimeoutExpired as e:
        return None

def main():
    if len(sys.argv)!=2:
        print(f"Usage: {sys.argv[0]} /path/to/solution",file=sys.stderr); return 2
    exe=Path(sys.argv[1]).resolve()
    if not exe.exists(): print(f"Executable not found: {exe}",file=sys.stderr); return 2
    passed=0; failed=[]
    with tempfile.TemporaryDirectory(prefix="yadro120_") as td:
        tmp=Path(td)
        # use test 001 as canonical valid source/expected for CLI special cases
        base_in=ROOT/"cases/001_scalar_zero.in"
        base_out=ROOT/"cases/001_scalar_zero.out"
        for idx,t in enumerate(MANIFEST,1):
            name=t["name"]; kind=t["kind"]
            ok=False; detail=""
            if kind=="valid":
                out=tmp/f"{name}.out"
                p=run([str(exe),"-i",str(ROOT/t["input_file"]),"-o",str(out)])
                if p is None: detail="TIMEOUT"
                elif p.returncode!=0: detail=f"rc={p.returncode}, stderr={p.stderr.decode(errors='replace').strip()}"
                elif not out.exists(): detail="output not created"
                elif out.read_bytes()!=(ROOT/t["output_file"]).read_bytes(): detail="binary output mismatch"
                else: ok=True
            elif kind=="invalid_input":
                out=tmp/f"{name}.out"
                p=run([str(exe),"-i",str(ROOT/t["input_file"]),"-o",str(out)])
                if p is None: detail="TIMEOUT"
                elif p.returncode==t["expected_rc"]: ok=True
                else: detail=f"expected rc={t['expected_rc']}, got {p.returncode}; stderr={p.stderr.decode(errors='replace').strip()}"
            else:
                mode=t["mode"]
                if mode=="no_args": cmd=[str(exe)]; cwd=None
                elif mode=="only_i": cmd=[str(exe),"-i",str(base_in)]; cwd=None
                elif mode=="only_o": cmd=[str(exe),"-o",str(tmp/"x.out")]; cwd=None
                elif mode=="flag_as_name": cmd=[str(exe),"-i","-o",str(tmp/"x.out")]; cwd=None
                elif mode=="missing_input": cmd=[str(exe),"-i",str(tmp/"does_not_exist.bin"),"-o",str(tmp/"x.out")]; cwd=None
                elif mode=="missing_output_dir": cmd=[str(exe),"-i",str(base_in),"-o",str(tmp/"no_such_dir"/"x.out")]; cwd=None
                elif mode=="leading_dash":
                    wd=tmp/"dash"; wd.mkdir(exist_ok=True)
                    shutil.copy2(base_in,wd/"-input.bin")
                    cmd=[str(exe),"-i","-input.bin","-o","-output.bin"]; cwd=wd
                elif mode=="same_path":
                    same=tmp/"same.bin"; shutil.copy2(base_in,same)
                    cmd=[str(exe),"-i",str(same),"-o",str(same)]; cwd=None
                p=run(cmd,cwd=cwd)
                if p is None: detail="TIMEOUT"
                elif p.returncode!=t["expected_rc"]: detail=f"expected rc={t['expected_rc']}, got {p.returncode}; stderr={p.stderr.decode(errors='replace').strip()}"
                elif mode=="leading_dash" and (cwd/"-output.bin").read_bytes()!=base_out.read_bytes(): detail="leading-dash output mismatch"
                elif mode=="same_path" and Path(cmd[-1]).read_bytes()!=base_out.read_bytes(): detail="same-path output mismatch"
                else: ok=True
            if ok:
                passed+=1; print(f"PASS {idx:03d}: {name}")
            else:
                failed.append((idx,name,detail)); print(f"FAIL {idx:03d}: {name}: {detail}")
    print(f"\nPassed {passed}/120 tests")
    if failed:
        print("Failures:")
        for i,n,d in failed: print(f"  {i:03d} {n}: {d}")
        return 1
    return 0

if __name__=="__main__": raise SystemExit(main())
'''
    (ROOT/"run_120_tests.py").write_text(runner,encoding="utf-8")
    os.chmod(ROOT/"run_120_tests.py",0o755)

    readme = "# 120 дополнительных тестов для YADRO C17\n\n"
    readme += "Набор построен строго по формату ТЗ: A/B/C interleaved, D signed int8, zero-padding, ядро без переворота, нормализация `%251`/`%241`.\n\n"
    readme += "## Состав\n\n- 98 валидных бинарных тестов с эталонными `.out`;\n- 14 тестов битого/усечённого ввода и невалидных размеров ядра;\n- 8 тестов CLI/путей (`return 10`, отсутствующие файлы, имя с `-`, input==output).\n\n"
    readme += "## Запуск\n\n```bash\ngcc -std=c17 -O2 -Wall -Wextra -Wpedantic solution.c -o solution\npython3 yadro_120_tests/run_120_tests.py ./solution\n```\n\n"
    readme += "Ожидаемый итог: `Passed 120/120 tests`. Каждый тест имеет таймаут 60 секунд.\n\n"
    readme += "## Важно\n\nТесты 108-111 (нулевые/чётные размеры D) и другие malformed-input cases выходят за гарантии валидного входа из ТЗ и проверяют только устойчивость/качество кода. Нулевые H/W тоже не оговорены ТЗ напрямую, но проверяются как защитный edge case.\n\n"
    readme += "Практический runtime-тест, который гарантированно переполняет 32-битный accumulator, намеренно не включён: для прямой свёртки он требует порядка миллиардов операций. Безопасность `int64_t` проверяется математической оценкой отдельно: `65535² * 255 * 128 = 140183454384000 < INT64_MAX`.\n\n"
    readme += "## Категории\n\n"
    for e in manifest:
        readme += f"- {e['name']}: {e['description']}\n"
    (ROOT/"README.md").write_text(readme,encoding="utf-8")

    # Preserve generator in suite for reproducibility.
    shutil.copy2(Path(__file__), ROOT/"generate_120_tests.py")
    print(ROOT)

if __name__ == "__main__":
    main()
