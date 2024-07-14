rm -rf ~/cheridb/output_cap
rm -rf ~/cheridb/output_nocap

scp -r christian@cheri.dos.cit.tum.de:~/ch_test/output_cap   ~/cheridb/output_cap
scp -r christian@cheri.dos.cit.tum.de:~/ch_test/output_nocap ~/cheridb/output_nocap