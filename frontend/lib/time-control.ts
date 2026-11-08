export function formatTimeControl(value:string|null|undefined):string|null{
  if(!value)return value??null;
  const match=value.trim().match(/^(\d+(?:\.\d+)?)(?:\+(\d+))?$/);
  if(!match)return value;
  const rawBase=Number(match[1]);
  // Recently imported records already use minutes; legacy records store seconds.
  if(rawBase<60)return `${match[1]}+${match[2]??'0'}`;
  const minutes=rawBase/60;
  const base=Number.isInteger(minutes)?String(minutes):String(Number(minutes.toFixed(2)));
  return `${base}+${match[2]??'0'}`;
}
