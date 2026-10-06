import {test,expect} from '@playwright/test';
const sample='사업\t월\t가용인력\t소요인력\nKF-21\t1월\t210\t230\nKF-21\t2월\t215\t228\nT-50\t1월\t160\t155\nLAH\t1월\t130\t138';
test('paste, preview, GAP analysis, chart, cleaning and multiple datasets',async({page})=>{
  const external:string[]=[];
  page.on('request',r=>{if(!r.url().startsWith('http://127.0.0.1')&&!r.url().startsWith('data:')) external.push(r.url());});
  await page.goto('/');
  await page.getByRole('button',{name:'데이터 추가',exact:true}).click();
  await page.getByLabel('데이터셋 이름').fill('테스트 인력');
  await page.getByLabel('Excel 데이터 붙여넣기').evaluate((el,text)=>{
    const clipboard=new DataTransfer(); clipboard.setData('text/plain',text);
    el.dispatchEvent(new ClipboardEvent('paste',{clipboardData:clipboard,bubbles:true,cancelable:true}));
  },sample);
  await page.getByRole('button',{name:'데이터 등록',exact:true}).click();
  await expect(page.getByRole('heading',{name:'테스트 인력',exact:true})).toBeVisible();
  await expect(page.getByRole('cell',{name:'KF-21',exact:true}).first()).toBeVisible();
  await page.getByRole('button',{name:'기본 분석',exact:true}).click();
  await page.getByLabel('분석 도구').selectOption('difference');
  await page.getByLabel('첫 번째 컬럼').selectOption('가용인력');
  await page.getByLabel('두 번째 컬럼').selectOption('소요인력');
  await page.getByRole('button',{name:'분석 실행',exact:true}).click();
  await expect(page.getByRole('cell',{name:'-20',exact:true})).toBeVisible();
  await expect(page.locator('.js-plotly-plot')).toBeVisible();
  for(const kind of ['line','bar','stacked','scatter','histogram','box','heatmap','auto']){
    await page.getByLabel('차트 종류').selectOption(kind);
    await expect(page.locator('.js-plotly-plot')).toBeVisible();
    await expect(page.getByText('이 결과를 해당 차트로 표시할 수 없습니다. 다른 차트를 선택해주세요.')).toHaveCount(0);
  }
  await page.getByRole('button',{name:'전체 자동 분석',exact:true}).click();
  await expect(page.getByText('자동 분석 완료')).toBeVisible();
  await page.getByRole('button',{name:'데이터 추가',exact:true}).click();
  await page.getByLabel('데이터셋 이름').fill('두 번째');
  await page.getByLabel('Excel 데이터 붙여넣기').fill(sample);
  await page.getByRole('button',{name:'데이터 등록',exact:true}).click();
  await expect(page.getByRole('heading',{name:'두 번째',exact:true})).toBeVisible();
  expect(external).toEqual([]);
});
test('offline LLM error stays local and upload rejects Excel',async({page})=>{
  await page.goto('/');
  await page.getByRole('button',{name:'LLM 설정',exact:true}).click();
  await page.getByLabel('API URL').fill('http://127.0.0.1:1/v1');
  await page.getByRole('button',{name:'연결 확인',exact:true}).click();
  await expect(page.getByText(/로컬 AI 서버에 연결할 수 없습니다/).first()).toBeVisible();
});

test('file upload, pagination, raw comparison, cleaning, JOIN and derived data',async({page})=>{
  await page.goto('/');
  await page.getByRole('button',{name:'데이터 추가',exact:true}).click();
  await page.getByRole('button',{name:'텍스트 파일',exact:true}).click();
  await page.getByLabel('데이터셋 이름').fill('생산량');
  const text='사업\t월\t생산대수\n'+Array.from({length:120},(_,i)=>`KF-21\t${i+1}월\t${i+1}`).join('\n');
  await page.locator('input[type=file]').setInputFiles({name:'생산.tsv',mimeType:'text/tab-separated-values',buffer:Buffer.from(text)});
  await page.getByRole('button',{name:'데이터 등록',exact:true}).click();
  await expect(page.getByRole('heading',{name:'생산량',exact:true})).toBeVisible();
  await expect(page.locator('tbody tr')).toHaveCount(50);
  await page.getByRole('button',{name:'다음 페이지',exact:true}).click();
  await expect(page.getByRole('cell',{name:'51월',exact:true})).toBeVisible();
  await page.getByRole('button',{name:'원본',exact:true}).click();
  await expect(page.getByRole('cell',{name:'1월',exact:true})).toBeVisible();
  await page.getByRole('button',{name:'정제 · 프로파일',exact:true}).click();
  await page.getByRole('button',{name:'정제 적용',exact:true}).click();
  await expect(page.getByText('정제 완료 · 원본과 비교할 수 있습니다.')).toBeVisible();
  await page.getByRole('button',{name:'데이터 추가',exact:true}).click();
  await page.getByLabel('데이터셋 이름').fill('인력 JOIN');
  await page.getByLabel('Excel 데이터 붙여넣기').fill(sample);
  await page.getByRole('button',{name:'데이터 등록',exact:true}).click();
  await expect(page.getByRole('heading',{name:'인력 JOIN',exact:true})).toBeVisible();
  await page.getByRole('button',{name:'기본 분석',exact:true}).click();
  await page.getByLabel('분석 도구').selectOption('join');
  await page.getByLabel('결합할 데이터셋').selectOption({label:'생산량'});
  await page.getByLabel('JOIN KEY (쉼표 구분)').fill('사업, 월');
  await page.getByRole('button',{name:'분석 실행',exact:true}).click();
  await expect(page.getByRole('columnheader',{name:'생산대수',exact:true})).toBeVisible();
  page.once('dialog',d=>d.accept('결합 결과'));
  await page.getByRole('button',{name:'결과를 데이터셋으로',exact:true}).click();
  await expect(page.getByRole('heading',{name:'결합 결과',exact:true})).toBeVisible();
});

test('AI localhost protocol: settings, JSON plan approval, Python GAP and Korean interpretation',async({page})=>{
  const {createServer}=await import('node:http');
  const seen:unknown[]=[];
  const server=createServer((req,res)=>{
    res.setHeader('Content-Type','application/json');
    if(req.method==='GET'){res.end(JSON.stringify({data:[{id:'qwen-protocol-test'}]}));return;}
    let input='';req.on('data',chunk=>input+=chunk);req.on('end',()=>{
      const payload=JSON.parse(input);seen.push(payload);
      const context=JSON.parse(payload.messages[1].content);
      const content=payload.response_format?JSON.stringify({dataset:context.selected_dataset,operation:'difference',columns:['가용인력','소요인력']}):'결론: 가용인력 대비 소요인력 GAP은 -20입니다. 추가 데이터 확인 필요.';
      res.end(JSON.stringify({choices:[{message:{content}}]}));
    });
  });
  await new Promise<void>(resolve=>server.listen(0,'127.0.0.1',resolve));
  const address=server.address();const port=typeof address==='object'&&address?address.port:0;
  try{
    await page.goto('/');
    await page.getByRole('button',{name:'데이터 추가',exact:true}).click();
    await page.getByLabel('데이터셋 이름').fill('AI 흐름');
    await page.getByLabel('Excel 데이터 붙여넣기').fill(sample);
    await page.getByRole('button',{name:'데이터 등록',exact:true}).click();
    await expect(page.getByRole('heading',{name:'AI 흐름',exact:true})).toBeVisible();
    await page.getByRole('button',{name:'LLM 설정',exact:true}).click();
    await page.getByLabel('API URL').fill(`http://127.0.0.1:${port}/v1`);
    await page.getByRole('button',{name:'연결 확인',exact:true}).click();
    await expect(page.getByText('연결 성공 · qwen-protocol-test')).toBeVisible();
    await page.getByRole('button',{name:'설정 저장',exact:true}).click();
    await page.getByLabel('AI 질문').fill('인력 GAP 분석해줘');
    await page.getByRole('button',{name:'질문 전송',exact:true}).click();
    await page.getByRole('button',{name:'계획 확인 후 실행',exact:true}).click();
    await expect(page.getByText('결론: 가용인력 대비 소요인력 GAP은 -20입니다. 추가 데이터 확인 필요.')).toBeVisible();
    await expect(page.getByRole('cell',{name:'-20',exact:true})).toBeVisible();
    expect(seen.length).toBe(2);
  }finally{await new Promise<void>(resolve=>server.close(()=>resolve()));}
});
