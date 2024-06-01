function result = validvariance(imagedata,varargin)
   if nargin > 1
       varcell = varargin(1);
       acrossvol= varcell{1};
   else
       acrossvol=0;
   end

   if acrossvol == 0
      result = var(imagedata(~isnan(imagedata) & ~isinf(imagedata)));
   else
      sz = size(imagedata);
      if length(sz) > 3
         dimt=sz(4);
      else
         dimt = 1;
      end

      if dimt > 1
          result = zeros(1,dimt);
          for vol = 1:dimt
              imagevol = imagedata(:,:,:,vol);
              result(vol) = var(imagevol(~isnan(imagevol) & ~isinf(imagevol)));
          end
      else
          result = var(imagedata(~isnan(imagedata) & ~isinf(imagedata)));
      end
   end
end
