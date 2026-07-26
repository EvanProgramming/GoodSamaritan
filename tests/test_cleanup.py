from good_samaritan.cleanup import cleanup_attempt_artifacts, cleanup_orphan_workspaces

def test_cleanup_never_leaves_work_root(tmp_path):
    work=tmp_path/'work';(work/'attempt-a').mkdir(parents=True);(work/'attempt-a'/'x').write_text('x');(work/'keep').mkdir();(work/'attempt-7.patch').write_text('patch');(work/'attempt-7-pr.md').write_text('draft')
    assert len(cleanup_orphan_workspaces(work))==1 and (work/'keep').exists()
    assert len(cleanup_attempt_artifacts(work,7))==2
