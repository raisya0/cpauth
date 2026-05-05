curl -k -s "https://mail.imago.net.co:2087/cpsess4154947525/" \
  -H "Cookie: whostmgrsession=:5txWek51fafjaIVg" \
  | grep -oP '(?<=<title>).*?(?=</title>)'
