volatile unsigned short dem;
static long bo_dem_phu(long x, long y){ long t[8]; t[0]=x; return t[0] / y; }
static long loc(long x){ long buf[16]; buf[0]=x; return bo_dem_phu(buf[0], 3); }
long tinh(long x){ long z[32]; z[0]=loc(x); return z[0]; }
int main(void){ dem++; return (int)tinh(7); }
