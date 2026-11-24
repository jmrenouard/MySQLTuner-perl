#!/usr/bin/env perl
# ===========================================================================
# Test:        tests/unit_docs_tutorials_howtos.t
# Description: Executable verification wrapper for tutorials, STE how-to guides,
#              CLI/MCP contracts, Mermaid/ASCII diagrams, math hygiene, and
#              MkDocs English isolation.
# Author:      Jean-Marie Renouard / Antigravity
# Project:     MySQLTuner-perl
# ===========================================================================
use strict;
use warnings;
use Test::More;
use FindBin;
use File::Spec;
use Cwd qw(abs_path);

my $PROJECT_ROOT = abs_path( File::Spec->catdir( $FindBin::Bin, '..' ) );

sub has_binary {
    my ($bin) = @_;
    for my $dir ( File::Spec->path() ) {
        my $candidate = File::Spec->catfile( $dir, $bin );
        return $candidate if -f $candidate && -x $candidate;
    }
    return undef;
}

sub find_python_bin {
    my $venv_py = File::Spec->catfile( $PROJECT_ROOT, '.venv-docs', 'bin', 'python' );
    return $venv_py if -f $venv_py && -x $venv_py;
    return has_binary('python3') || has_binary('python');
}

sub has_lf_only {
    my ($path) = @_;
    open my $fh, '<:raw', $path or die "Cannot read $path: $!";
    local $/;
    my $raw = <$fh>;
    close $fh;
    return index( $raw, "\r" ) == -1 ? 1 : 0;
}

subtest 'LF line endings and Perl syntax check' => sub {
    my @files = (
        File::Spec->catfile( $PROJECT_ROOT, 'mkdocs.yml' ),
        File::Spec->catfile( $PROJECT_ROOT, 'docs', '02-how-to-guides', 'operations', 'run-offline-verification.md' ),
        File::Spec->catfile( $PROJECT_ROOT, 'tests', 'unit_docs_tutorials_howtos.py' ),
    );
    for my $path (@files) {
        ok( -f $path, "$path exists" );
        ok( has_lf_only($path), "$path uses Unix LF line endings" );
    }

    my $pl_path = File::Spec->catfile( $PROJECT_ROOT, 'mysqltuner.pl' );
    my $syntax  = qx("$^X" -c "$pl_path" 2>&1);
    my $rc      = $? >> 8;
    is( $rc, 0, 'perl -c mysqltuner.pl exits 0' );
    like( $syntax, qr/syntax OK/, 'mysqltuner.pl passes perl -c syntax check' );
};

subtest 'Executable Python documentation, CLI, MCP, Mermaid, and math checks' => sub {
    my $python_bin = find_python_bin();
    ok( defined $python_bin, 'Python 3 binary available' );

    my $py_test = File::Spec->catfile( $PROJECT_ROOT, 'tests', 'unit_docs_tutorials_howtos.py' );
    my $out     = qx("$python_bin" -B "$py_test" 2>&1);
    my $rc      = $? >> 8;
    is( $rc, 0, "unit_docs_tutorials_howtos.py passed: $out" );
    like( $out, qr/\bOK\s*$/s, 'Python test suite emitted OK' );
};

done_testing();
