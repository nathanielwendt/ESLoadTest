
requests=( 4 8 16 32 64 )
cat_size=( "small" "medium" "large" "xlarge" )

for c in "${cat_size[@]}"
do
  :
  echo 'catalog' $c
  for r in "${requests[@]}"
  do
    :
    doublesize="$((2 * $r))"
    echo 'size' $doublesize
    #rm data/peak-$c-$doublesize.csv
    for i in {1..5};
    do
      python req.py $r $c >> data/peak-$c-$doublesize.csv;
    done
    python compute.py data/peak-$c-$doublesize.csv
  done
done
