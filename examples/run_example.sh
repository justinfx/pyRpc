#!/usr/bin/env bash
python server.py &
TEST_SERVER=$!

python client.py &
wait $!
TEST_EXIT_CODE=$?

kill $TEST_SERVER

if [ -z ${TEST_EXIT_CODE+x} ] || [ "$TEST_EXIT_CODE" -ne 0 ] ; then
  printf "${RED}Tests Failed${NC} - Exit Code: $TEST_EXIT_CODE\n"
else
  printf "${GREEN}Tests Passed${NC}\n"
fi

exit $TEST_EXIT_CODE
