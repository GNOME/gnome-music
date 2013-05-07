TESTS = \
    tests_albumArt.js \
    $(NULL)

check-TESTS:
	@RUN_TESTS_ENV_VARS= \
	     LD_LIBRARY_PATH=$(top_srcdir)/libgd/.libs:$$LD_LIBRARY_PATH \
	     GI_TYPELIB_PATH=$(top_srcdir)/libgd:$$GI_TYPELIB_PATH ; \
	 for test in $(TESTS) ; do \
	   echo "Running suite $$test" ; \
	   $(RUN_TESTS_ENV_VARS) gjs $$test ; \
	   status=$$? ; \
	   if [[ $$status -ne 0 ]] ; then exit 1 ; fi ; \
	 done

-include $(top_srcdir)/git.mk
