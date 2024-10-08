rsync -avz --exclude '*.o' --exclude '*.out' --exclude '*.a' --exclude '*.so' --exclude '*.db' \
    ~/cheridb/structures christian@cheri.dos.cit.tum.de:~/ch_test/structures