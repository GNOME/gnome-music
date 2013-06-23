TESTS = \
	tests_albumArt.js \
	tests_albumPlayback.js \
	tests_artistsPlayback.js \
	$(NULL)

EXTRA_DIST = $(TESTS)

TESTS_ENVIRONMENT = \
	LD_LIBRARY_PATH=$(top_builddir)/libgd/.libs:$$LD_LIBRARY_PATH \
	GI_TYPELIB_PATH=$(top_builddir)/libgd:$$GI_TYPELIB_PATH

check-TESTS:
	for test in $(TESTS) ; do \
		echo "Running suite $$test" ; \
		$(TESTS_ENVIRONMENT) gjs --include-path=$(top_srcdir)/src $(srcdir)/$$test ; \
		status=$$? ; \
		if [[ $$status -ne 0 ]] ; then exit 1 ; fi ; \
	done

-include $(top_srcdir)/git.mk
