// LZE
// Copyright (C)1995,2008 GORRY.
// Porting for C# by Kei Moroboshi(@kmoroboshi),Oct/2018-Jul/2020
//  Thanks to @Jr200Okada-san and @tokihiro_naito-san
//How to build lze.exe:
// %WINDIR%\Microsoft.NET\Framework\v4.0.30319\csc lze.cs

/********************************************************************************/

#define	BZCOMPATIBLE
#define	SPEED

using System;
using System.Data;
using System.IO;
using System.Text;

public partial class lze {
	 const int EXIT_FAILURE=1;
	 const int EXIT_SUCCESS=0;
	 const int EOF=-1;
//	 const int BZCOMPATIBLE=1;	/* 0 or 1 */
//	 const int SPEED=1;		/* 0 or 1 */
	 const int N=16384;
	 const int F=256;
#if	SPEED
	 const int IDX=8192;
#else
	 const int IDX=256;
#endif

	static FileStream infile;
	static FileStream outfile;
	static ulong outcount = 0;
	static byte []text = new byte[(N+F)*256];
	static int []son = new int[N+1+IDX];
	static int []dad = new int[N+1+IDX];
	static int []same = new int[N];

	 const int NIL=-1;

	static int matchpos, matchlen, noder, nodeo;
	static int samecount;

/********************************************************************************/

static void error( String mes )
{
	Console.WriteLine( mes );
	Environment.Exit(EXIT_FAILURE) ;
}

static void init_tree()
{
	int	i;

	for ( i=0; i<N+1; i++ ) {
		son[i] = NIL;
		dad[i] = NIL;
	}
	for ( i=0; i<IDX; i++ ) {
		son[N+1+i] = NIL;
		dad[N+1+i] = NIL;
	}
}

static void insert_node( int r )
{
	int	pr;
	int	k, o;

	if ( samecount > 0 ) {
		same[r] = samecount;
		samecount--;
	} else {
		int	i;
		byte	c;

		pr = r;			//p = &text[r];
		c = text[pr++];		//c = *(p++);
		for ( i=0; i<F-1; i++ ) {
			if ( text[pr++] != c ) { 
				break;
			}
		}
		samecount = i;
		same[r] = samecount;
		samecount--;
	}

#if SPEED
	k = (text[r]<<5) ^ (text[r+1] );
#else
	k = text[r];
#endif
	o = son[N+1+k];
	son[N+1+k] = r;
	nodeo = o;
	noder = r;
	if ( o < 0 )  /* if ( o == NIL )  */
	{
		dad[N+1+k] = r;
		return;
	}
	son[r] = o;
	dad[o] = r;
	dad[r] = NIL;

	return;
}

static void	delete_node( int p )
{
	int	k, q, r;

#if SPEED
	k = (text[p]<<5) ^ (text[p+1] );
#else
	k = text[p];
#endif
	r = N+1+k;
	q = dad[r];
	do {
		if ( q < 0 ) {
			return; /* if ( q == NIL ) return; */
		}
		if ( p == q ) {
			if ( dad[q] < 0 ) { /* if ( dad[q] == NIL ) { */
				son[N+1+k] = son[q];
			} else {
				son[dad[q]] = son[q];
			}
			dad[r] = dad[q];
			dad[q] = NIL;
			return;
		}
		r = q;
		q = dad[q];
	} while (true);

//	return;
}

static int	get_node()
{
	int	r, o, m, n;
	int	mlen;

	mlen = 0;
	o = nodeo;
	r = noder;
	if ( o < 0 ) { /* if ( o == NIL ) { */
		return (mlen);
	}

	n = same[r];
	do {
		int	pi,qi;	//unsigned char	*p, *q;
		int	i;

		m = (r-o) & (N-1);
		if ( m > 8192 ) return (mlen);
		i = mlen;
		pi = r+i+1;		//p = &text[r+i+1];
		qi = o+i+1;		//q = &text[o+i+1];

		if ( i!=0 ) { i--; if ( text[--pi] != text[--qi] ) { continue;} }
		if ( i!=0 ) { i--; if ( text[--pi] != text[--qi] ) { continue;} }
		if ( i!=0 ) { i--; if ( text[--pi] != text[--qi] ) { continue;} }
		if ( i!=0 ) { i--; if ( text[--pi] != text[--qi] ) { continue;} }

		i = n;
		if ( i > same[o] ) {
			i = same[o];
		}
		pi = r+i;		//p = &text[r+i];
		qi = o+i;		//q = &text[o+i];
		if ( text[pi++] != text[qi++] )	//if ( *(p++) != *(q++) )
		{
			continue;
		}
		for ( ; i<F; ) {
			i++; if ( text[pi++] != text[qi++] ) { break; }
			i++; if ( text[pi++] != text[qi++] ) { break; }
			i++; if ( text[pi++] != text[qi++] ) { break; }
			i++; if ( text[pi++] != text[qi++] ) { break; }
		}
		if ( i>F ) {
			i=F;
		}
		if ( mlen < i ) {
			matchpos = m;
			mlen = i;
			if ( i >= F ) { return (mlen); }
		}
	} while ( (o=son[o]) >= 0 ); /* } while ( (o=son[o]) != NIL ); */

	return (mlen);
}

/********************************************************************************/

static uint	flags;
static int	flagscnt;
static int	codeptr, code2size;
static byte[] code = new byte[ 256 ];
static byte[] code2 = new byte[4];

static void	init_putencode()
{
	code[0] = 0;
	codeptr = 1;
	flags = 0;
	flagscnt = 0;
}

static void	sub_putencode( byte c )
{
	outfile.WriteByte( c );
}

static int	putencode( int r )
{
	int	size;
	uint	fl;
	int	fc;
	int	mlen;
	int	mpos;

	fl = flags;
	fc = flagscnt;
	mlen = matchlen;
	mpos = matchpos;
	size = 0;
	if ( mlen < 2 ) {
		matchlen = 1;
		fl = (fl+fl)+1;
		fc += 1;
		code2[0] = text[r];
		code2size = 1;
	} else {
		if (false) {
		} else if ( ( mlen < 6 ) && ( mpos < 257 ) ) {
			fl = (uint)( (fl<<4)+(mlen-2) );
			fc += 4;
			mpos = 256-mpos;
			code2[0] = (byte) (mpos);
			code2size = 1;
		} else if ( mlen > 9 ) {
			fl = (uint)( (fl<<2)+1 );
			fc += 2;
			mpos = 8192-mpos;
			code2[0] = (byte) (mpos>>5);
			code2[1] = (byte) (mpos<<3);
			code2[2] = (byte) (mlen-1);
			code2size = 3;
		} else if ( mlen > 2) {
			fl = (uint) ( (fl<<2)+1 );
			fc += 2;
			mpos = 8192-mpos;
			code2[0] = (byte) (mpos>>5);
			code2[1] = (byte) ( (mpos<<3)|(mlen-2) );
			code2size = 2;
		} else {
			matchlen = 1;
			fl = (uint) ( (fl+fl)+1 );
			fc += 1;
			code2[0] = text[r];
			code2size = 1;
		}
	}
	if ( fc > 8 ) {
		int	i;
		int pi;

		fc -= 8;
		pi=0;
		code[pi] = (byte)(fl>>fc);	//*(p) = (fl>>fc);
//		DebugMacro( (Debug),  printf( "output code=" ) );
		for ( i=0; i<codeptr; i++ ) {
			sub_putencode( code[pi++] );	//	sub_putencode( *(p++) );
//			DebugMacro( (Debug), printf( "$%02X ", code[i] ) );
		}
//		DebugMacro( (Debug), printf( "\n" ) );
		size += codeptr;
		codeptr = 1;
		fl &= (byte)(0x00ff>>(8-fc));
	}
//	DebugMacro( (Debug), printf( "store code($%02X)=", codeptr ) );
	{
		int pi,qi;
		int	i;

		pi = codeptr;
		qi = 0;
		for ( i=0; i<code2size; i++ ) {
			code[pi++] = code2[qi++];
//			DebugMacro( (Debug),  printf( "$%02X ", code2[i] ) );
		}
		codeptr += i;
	}
//	DebugMacro( (Debug), printf( "\n" ) );

	flags = fl;
	flagscnt = fc;

	return (size);
}

static int	finish_putencode()
{
	int	i;
	int	size;

	size = 0;
	flags = (flags+flags)+0;
	flags = (flags+flags)+1;
	flagscnt += 2;
	code2[0] = (byte) 0;
	code2[1] = (byte) 0;
	code2[2] = (byte) 0;
	code2size = 3;
	if ( flagscnt > 8 ) {
		flagscnt -= 8;
		code[0] = (byte) (flags>>flagscnt);
//		DebugMacro( (Debug), printf( "output code=" ) );
		for ( i=0; i<codeptr; i++ ) {
			outfile.WriteByte( code[i] );
//			DebugMacro( (Debug), printf( "$%02X ", code[i] ) );
		}
//		DebugMacro( (Debug), printf( "\n" ) );
		size += codeptr;
		codeptr = 1;
		flags &= (byte)(0x00ff>>(8-flagscnt));
	}
//	DebugMacro( (Debug), printf( "store code($%02X)=", codeptr ) );
	for ( i=0; i<code2size; i++ ) {
		code[codeptr++] = code2[i];
//		DebugMacro( (Debug), printf( "$%02X ", code2[i] ) );
	}
//	DebugMacro( (Debug), printf( "\n" ) );

	if ( flagscnt > 0 ) {
		code[0] = (byte)(flags<<(8-flagscnt));
	}
	if ( codeptr > 1 ) {
//		DebugMacro( (Debug), printf( "output code=" ) );
		for ( i=0; i<codeptr; i++ ) {
			outfile.WriteByte( code[i] );
//			DebugMacro( (Debug),  printf( "$%02X ", code[i] ) );
		}
//		DebugMacro( (Debug), printf( "\n" ) );
		size += codeptr;
	}

	return (size);
}

/********************************************************************************/

static void	encode()
{
	int 	i, c, r, s, len, mlen;
	bool	ok_delete_node;
	ulong 	incount = 0, printcount = 0, cr;

	ok_delete_node = false;
	init_tree();
	init_putencode();
	s = 0;
	r = N-F;
	for ( i=s; i<r; i++ ) {
		text[i] = 0;
	}
	for ( i=0; i<F; i++ ) {
		c = infile.ReadByte();
		if ( c == EOF ) {
			break;
		}
		text[r+i] = (byte)c;
	}
	incount = (uint)i;
	len = i;
	if ( incount == 0 ) {
		return;
	}
#if BZCOMPATIBLE
	insert_node( r );
	sub_putencode( text[r] );
	c = infile.ReadByte();
	incount++;
	if ( c != EOF ) {
		text[s] = (byte)c;
		if ( s < (F-1) ) {
			text[s+N] = (byte)c;
		}
		s = (s+1) & (N-1);
		r = (r+1) & (N-1);
	} else {
		s = (s+1) & (N-1);
		r = (r+1) & (N-1);
		len--;
		if ( len == 0 ) 	//if ( !len )
		{
			goto NoEncode;
		}
	}
#endif
	insert_node( r );
	do {
		matchlen = get_node();
		if ( matchlen > len ) { 
			matchlen = len;
		}
		outcount += (ulong)putencode( r );

//		DebugMacro( (Debug), printf( "text[r]=$%02X r=%4d s=%4d matchpos=%4d matchlen=%4d\n", text[r], r, s, matchpos, matchlen ) );

		matchpos = N+1;
		mlen = matchlen;
		for ( i=0; i<mlen; i++ ) {
			c = infile.ReadByte();
			if ( c ==EOF ) {
				break;
			}
			if ( ok_delete_node ) {
				delete_node(s);
			} else {
				if ( s == N-F-1 ) {
					ok_delete_node = true;
				}
			}
			text[s] = (byte)c;
			if ( s < (F-1) ) {
				text[s+N] = (byte)c;
			}
			s = (s+1) & (N-1);
			r = (r+1) & (N-1);
			insert_node(r);
		}
		if ( (incount+=(ulong)i) > printcount ) {
			Console.Write( incount.ToString() + "\r" );
//			printf( "%12lu\r", incount );
			printcount += 1024*16;
		}
		while ( i++ < mlen ) {
			if ( ok_delete_node ) {
				delete_node(s);
			} else {
				if ( s == N-F-1 ) {
					ok_delete_node = true;
				}
			}
			s = (s+1) & (N-1);
			r = (r+1) & (N-1);
			if ( --len != 0 )
			{
				insert_node(r);
			}
		}
	} while ( len > 0 );

  NoEncode:;
	outcount += (ulong)finish_putencode();
//	printf( "In : %lu bytes\n", incount );
//	printf( "Out: %lu bytes\n", outcount );
	Console.WriteLine( "In  : "+incount.ToString()  + " bytes" );
	Console.WriteLine( "Out : "+outcount.ToString() + " bytes" );
	if ( incount != 0 ) {
		cr = ( 1000 * outcount + (incount/2) ) / incount;
//!!!		printf( " Out/In: %lu.%03lu\n", cr/1000, cr%1000 );
		Console.WriteLine( " Out/In: "+(cr/1000).ToString()+"."+(cr%1000).ToString("000") );
	}
}


static void	decode( ulong size )
{
	uint	flags;
	int	flagscnt;
	int	i, j, k, r, c;
	uint	u;
	int	bit;

	r = N-F;
#if BZCOMPATIBLE
	if ( (c=infile.ReadByte())==EOF ) {
		goto Err;
	}
	outfile.WriteByte( (byte)c );
	text[r++] = (byte)c;
	r &= (N-1);
#endif
	flags = 0;
	flagscnt = 0;
	do {
//		GetBit();
		if ((--flagscnt)<0) {
			if ((c = infile.ReadByte()) == EOF ) {
				goto Err;
			}
			flags = (uint)c;
			flagscnt += 8;
		}
		bit = (int)( (flags<<=1) & 256 );
		if (bit != 0 ) {
						/* 1 */
			if ( (c=infile.ReadByte()) == EOF ) {
				break;
			}
//			DebugMacro( (Debug>99), printf( "1($%02X) ", c ) );
			outfile.WriteByte( (byte)c );
//			DebugMacro( (Debug), printf( "text[r]=$%02X r=%4d \n", c, r ) );
			text[r++] = (byte)c;
			r &= (N-1);
		} else {
//			GetBit();
			if ((--flagscnt)<0) {
				if ((c = infile.ReadByte()) == EOF ) {
					goto Err;
				}
				flags = (uint)c;
				flagscnt += 8;
			}
			bit = (int)( (flags<<=1) & 256 );
			if (bit != 0) {
						/* 01 */
				if ( (i=infile.ReadByte() )==EOF ) {
					goto Err;
				}
				if ( (j=infile.ReadByte() )==EOF ) {
					goto Err;
				}
//				DebugMacro( (Debug>99), printf( "01($%02X,$%02X) ", i, j ) );
				u = (uint) ( (i<<8) | j );
				j = (int)( u & 7);
				u >>= 3;
				if ( j == 0 ) {
					if ((j = infile.ReadByte()) == EOF ) {
						goto Err;
					}
//					DebugMacro( (Debug>99), printf( "($%02X) ", j ) );
					if ( j==0 ) {
						goto Quit;
					}
					j++;
				} else {
					j += 2;
				}
				i = (int)( r-(8192-u) );
			} else {
						/* 00 */
//				GetBit();
				if ((--flagscnt)<0) {
					if ((c = infile.ReadByte()) == EOF ) {
						goto Err;
					}
					flags = (uint)c;
					flagscnt += 8;
				}
				bit = (int)( (flags<<=1) & 256 );
				j  = ( bit!=0 ? 2 : 0 );
//				GetBit();
				if ((--flagscnt)<0) {
					if ((c = infile.ReadByte()) == EOF ) {
						goto Err;
					}
					flags = (uint)c;
					flagscnt += 8;
				}
				bit = (int)( (flags<<=1) & 256 );

				j += ( bit != 0 ? 1 : 0 );
				j += 2;
				if ( (i=infile.ReadByte() ) == EOF )
				{
					goto Err;
				}
//				DebugMacro( (Debug>99), printf( "00($%02X) ", i ) );
				i = r-(256-i);
			}
			for ( k=0; k<j; k++ ) {
				c = text[(i+k) & (N-1)];
				outfile.WriteByte( (byte)c );
//				DebugMacro( (Debug), printf( "text[r]=$%02X j=%4d r=%4d i=%4d \n", c, j, r, i ) );
				text[r++] = (byte)c;
				r &= (N-1);
			}
		}
	} while (true);
  Quit:;
  Err:;
//	printf( "%12lu\n", size );
	Console.WriteLine( size.ToString() );
}

static void	Usage()
{
	Console.Write(
	  "Usage: lze e infile outfile (Encode)\n"
	 +"       lze d infile outfile (Decode)\n"
	);
	Environment.Exit(EXIT_FAILURE);
}

static int Main( string[] args )
{
	ulong 	size;
//	char	*inbuf;
//	char	*outbuf;

	if (  args.Length != 3 ) {
		Usage();
	}

	var sw = new System.Diagnostics.Stopwatch();
	sw.Start();

	infile = new FileStream( args[1] ,FileMode.Open, FileAccess.Read );
//	if ( infile == NULL ) error( "Error: Open Input File" );
	outfile = new FileStream( args[2] ,FileMode.Create, FileAccess.Write );
//	if ( outfile == NULL ) error( "Error: Open Output File" );
/*
	if ( NULL != ( inbuf = malloc( 16*1024 ) ) ) {
		setvbuf( infile, inbuf, _IOFBF, 16*1024 );
	}
	if ( NULL != ( outbuf = malloc( 16*1024 ) ) ) {
		setvbuf( outfile, outbuf, _IOFBF, 16*1024 );
	}
*/
	switch( args[0] ) {
	  case "E":
	  case "e":
//		fseek( infile, 0L, SEEK_END );
		size = (ulong)infile.Length;
		outfile.WriteByte( (byte)(size>>24) );
		outfile.WriteByte( (byte)(size>>16) );
		outfile.WriteByte( (byte)(size>> 8) );
		outfile.WriteByte( (byte)(size>> 0) );

		encode();
		break;
	  case "D":
	  case "d":
		size  = ((ulong )infile.ReadByte() << 24);
		size |= ((ulong )infile.ReadByte() << 16);
		size |= ((ulong )infile.ReadByte() <<  8);
		size |= ((ulong )infile.ReadByte() <<  0);
		decode( size );
		break;
	}
	infile.Close();
	outfile.Close();

	sw.Stop();
	Console.WriteLine( @"Time: {0:s\.ffffff}s" , sw.Elapsed );
//!!!	printf( "Time: %fs\n", ((double)clock())/CLK_TCK );
	return (EXIT_SUCCESS);
}

}

