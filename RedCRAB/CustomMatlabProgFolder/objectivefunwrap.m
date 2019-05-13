function [ FOM, Std ] = objectivefunwrap(pulses, timegrid)
%   objectivefun Evaluates the objective function to be extremized
%   Often, the dynamical system is integrated and an objective such as
%   state overlap and/ or fluence or some expectation value of an observable is calculated as
%   figure of merit (FOM) \pm Std. If not standard deviation (std) information is available, still
%   return the second argument 'Std' - just as 0.0




u1 = pulses(1,:);
%u2 = pulses(2,:);
%u3 = pulses(3,:);
%u4 = pulses(4,:);

%FOM = sum(abs(u1-1));
Std = rand();

FOM = Main_so(u1);


end

