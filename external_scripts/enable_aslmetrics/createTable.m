function T = createTable(structarray,VariableNames)

LEN=length(structarray);

field = VariableNames(1);
column  = extractfield(structarray,sprintf("%s",field))';
if isa(column,'cell')
    vectorcol = [column{:}]';
else
    vectorcol = column
end
T = table(vectorcol,'VariableNames',field);

lastfield=field;
for fieldnum=2:length(VariableNames)
    field = VariableNames(fieldnum);
    column  = extractfield(structarray,sprintf("%s",field))'; 
    if isa(column,'cell')
        vectorcol = [column{:}]';
        if isa(column{1},'char')
            vectorcol = column;
        end
    else
        vectorcol = column;
        if LEN > length(vectorcol)
            vectorcol=double(NaN(LEN,1));
            for rownum=1:LEN
                fieldvalue = getfield(structarray,{rownum},field);
                if length(fieldvalue) > 0
                    vectorcol(rownum) = fieldvalue;
                end
            end
            
        end
    end
    T = addvars(T,vectorcol, 'After',sprintf('%s',lastfield),'NewVariableNames',sprintf('%s',field));
    lastfield=field;
end

