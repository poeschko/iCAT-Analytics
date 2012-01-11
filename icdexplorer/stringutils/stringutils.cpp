/*
  C++ implementation of
  "A linear space algorithm for computing maximal common subsequences"
  D. S. Hirschberg
  http://portal.acm.org/citation.cfm?id=360861

  See also: http://wordaligned.org/articles/longest-common-subsquence
*/

#include <Python.h>

#include <algorithm>
#include <iterator>
#include <vector>

#include <string>

typedef std::vector<int> lengths;

/*
  The "members" type is used as a sparse set for LCS calculations.
  Given a sequence, xs, and members, m, then
  if m[i] is true, xs[i] is in the LCS.
*/
typedef std::vector<bool> members;

/*
  Fill the LCS sequence from the members of a sequence, xs
  x - an iterator into the sequence xs
  xs_in_lcs - members of xs
  lcs - an output results iterator
*/
/*template <typename it, typename ot>
void set_lcs(it x, members const & xs_in_lcs, ot lcs)
{
    for (members::const_iterator xs_in = xs_in_lcs.begin();
         xs_in != xs_in_lcs.end(); ++xs_in, ++x)
    {
        if (*xs_in)
        {
            *lcs++ = *x;
        }
    }
}*/

/*
  Calculate LCS row lengths given iterator ranges into two sequences.
  On completion, `lens` holds LCS lengths in the final row.
*/
template <typename it>
void lcs_lens(it xlo, it xhi, it ylo, it yhi, lengths & lens)
{
    // Two rows of workspace.
    // Careful! We need the 1 for the leftmost column.
    lengths curr(1 + distance(ylo, yhi), 0);
    lengths prev(curr);

    for (it x = xlo; x != xhi; ++x)
    {
        swap(prev, curr);
        int i = 0;
        for (it y = ylo; y != yhi; ++y, ++i)
        {
            curr[i + 1] = *x == *y
                ? prev[i] + 1
                : std::max(curr[i], prev[i + 1]);
        }
    }
    swap(lens, curr);
}

/*
  Recursive LCS calculation.
  See Hirschberg for the theory!
  This is a divide and conquer algorithm.
  In the recursive case, we split the xrange in two.
  Then, by calculating lengths of LCSes from the start and end
  corners of the [xlo, xhi] x [ylo, yhi] grid, we determine where
  the yrange should be split.

  xo is the origin (element 0) of the xs sequence
  xlo, xhi is the range of xs being processed
  ylo, yhi is the range of ys being processed
  Parameter xs_in_lcs holds the members of xs in the LCS.
*/
template <typename it>
void
calculate_lcs(it xo, it xlo, it xhi, it ylo, it yhi, members & xs_in_lcs)
{
    unsigned const nx = distance(xlo, xhi);

    if (nx == 0)
    {
        // empty range. all done
    }
    else if (nx == 1)
    {
        // single item in x range.
        // If it's in the yrange, mark its position in the LCS
        xs_in_lcs[distance(xo, xlo)] = find(ylo, yhi, *xlo) != yhi;
    }
    else
    {
        // split the xrange
        it xmid = xlo + nx / 2;

        // Find LCS lengths at xmid, working from both ends of the range
        lengths ll_b, ll_e;
        std::reverse_iterator<it> hix(xhi), midx(xmid), hiy(yhi), loy(ylo);

        lcs_lens(xlo, xmid, ylo, yhi, ll_b);
        lcs_lens(hix, midx, hiy, loy, ll_e);

        // Find the optimal place to split the y range
        lengths::const_reverse_iterator e = ll_e.rbegin();
        int lmax = -1;
        it y = ylo, ymid = ylo;

        for (lengths::const_iterator b = ll_b.begin();
             b != ll_b.end(); ++b, ++e)
        {
            if (*b + *e > lmax)
            {
                lmax = *b + *e;
                ymid = y;
            }
            // Care needed here!
            // ll_b and ll_e contain one more value than the range [ylo, yhi)
            // As b and e range over dereferenceable values of ll_b and ll_e,
            // y ranges over iterator positions [ylo, yhi] _including_ yhi.
            // That's fine, y is used to split [ylo, yhi), we do not
            // dereference it. However, y cannot go beyond ++yhi.
            if (y != yhi)
            {
                ++y;
            }
        }
        // Split the range and recurse
        calculate_lcs(xo, xlo, xmid, ylo, ymid, xs_in_lcs);
        calculate_lcs(xo, xmid, xhi, ymid, yhi, xs_in_lcs);
    }
}

// Calculate an LCS of (xs, ys), returning the result in an_lcs.
/*template <typename seq, typename it>
void lcs(seq const & xs, seq const & ys, seq & an_lcs)
{
    members xs_in_lcs(xs.size(), false);
    it xbegin = xs.begin();
    calculate_lcs(xs.begin(), xs.begin(), xs.end(),
                  ys.begin(), ys.end(), xs_in_lcs);
    set_lcs(xs.begin(), xs_in_lcs, back_inserter(an_lcs));
}*/

template <typename seq>
int lcs_len(seq const & xs, seq const & ys)
{
	int result = 0;

    typename seq::const_iterator xbegin = xs.begin();
    typename seq::const_iterator ybegin = ys.begin();
    typename seq::const_iterator xend = xs.end();
    typename seq::const_iterator yend = ys.end();

    int same_start = 0;

    while (xbegin != xend && ybegin != yend && *xbegin == *ybegin) {
    	++xbegin;
    	++ybegin;
    	++result;
    	++same_start;
    }

    int xsize = xs.size() - same_start;

    //int reverse_same = 0;
    typename seq::const_reverse_iterator xrbegin = xs.rbegin();
    typename seq::const_reverse_iterator yrbegin = ys.rbegin();
    typename seq::const_reverse_iterator xrend = xs.rend() - same_start;
    typename seq::const_reverse_iterator yrend = ys.rend() - same_start;

    while (xrbegin != xrend && yrbegin != yrend && *xrbegin == *yrbegin) {
    	++xrbegin;
    	++yrbegin;
    	++result;
    	--xsize;
    	--xend;
    	--yend;
    }

    members xs_in_lcs(xsize, false);

    calculate_lcs(xbegin, xbegin, xend,
                  ybegin, yend, xs_in_lcs);
    //int result = 0;
    for (members::const_iterator xs_in = xs_in_lcs.begin();
             xs_in != xs_in_lcs.end(); ++xs_in)
    {
    	if (*xs_in)
    	{
    		++result;
    	}
    }
    return result;
    //set_lcs(xs.begin(), xs_in_lcs, back_inserter(an_lcs));
}

static PyObject *
lcs_length(PyObject *self, PyObject *args)
{
    const char *s1;
    const char *s2;
    //int sts;

    if (!PyArg_ParseTuple(args, "ss", &s1, &s2))
        return NULL;
    //sts = system(command);

    //const std::string string1(s1);
    //const std::string string2(s2);

    //std::string res;
    //lcs(std::string(s1), std::string(s2), res);
    //int result = res.size();

    int result = lcs_len(std::string(s1), std::string(s2));

    return Py_BuildValue("i", result);
}

static PyMethodDef ModuleMethods[] = {
    {"lcs_length",  lcs_length, METH_VARARGS,
     "Calculate the length of a longest common subsequence of two strings."},
    {NULL, NULL, 0, NULL}        /* Sentinel */
};

PyMODINIT_FUNC
initstringutils(void)
{
	PyObject *m;

	m = Py_InitModule("stringutils", ModuleMethods);
	if (m == NULL)
		return;
}
