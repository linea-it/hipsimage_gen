

for i in {0..12}; do java -jar /home/singulani/Aladin.jar -hipsgen id=CDS/P/DC2/color order=$i in=/mnt/EXT4/datasets/DC2/images/g/ out=/home/singulani/projects/hipsimage_gen/test INDEX &; done


for pair in "139441405,139442114" "139452928,139452930"; do
  i=${pair%,*}
  a=${pair#*,}
  echo "java -jar /home/singulani/Aladin.jar -hipsgen id=CDS/P/DC2/color region="12/$i-$a" mode=overwrite in=/mnt/EXT4/datasets/DC2/images/g/ out=/home/singulani/projects/hipsimage_gen/test TILES"
  nohup java -jar /home/singulani/Aladin.jar -hipsgen id=CDS/P/DC2/color region="12/$i-$a" mode=overwrite in=/mnt/EXT4/datasets/DC2/images/g/ out=/home/singulani/projects/hipsimage_gen/test TILES > "/home/singulani/projects/hipsimage_gen/test/$i.$a.log" 2>&1 &
done

