#!/bin/bash
for template in `ls *ryant*`
do newtemplate=$(echo $template | awk -F "ryant" {'print $1'})
   newtemplate=${newtemplate}trouard.pbs
   cp $template $newtemplate
   sed -i s/ryant/trouard/g $newtemplate
done
