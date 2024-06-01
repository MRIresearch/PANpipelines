function result = glob(pattern)
filestruct=dir(pattern);
if length(filestruct) > 0
filename = filestruct.name;
filedir = filestruct.folder;
result = fullfile(filedir,filename);
else
result = "";
end