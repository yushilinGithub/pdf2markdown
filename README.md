# 原始页面
截取了 pdf 中的一页，如下图所示

![image](https://github.com/user-attachments/assets/67b08d13-502f-4e74-ad50-81fce03036ed)


# 解析效果
如下是解析后的 markdown 文件，表格用 html 表示，也可转化成 markdown，latex。


![image](https://github.com/user-attachments/assets/425a8b53-15b9-476e-ae62-31e5750d78fb)

```
{
    file_name: xxx,   // 文档名称
    json_tree:{        // 根据标题层级分的树形结构
        type: title,
        id: xxx,
        text: xxx,
        elements: [{
                    type: figure,  //图片
                    id: xxx,
                    figure_title: xxx,   //图片的标题
                    figure_url: xxx,  # or figure_url   //图片的存储地址
                    figure_footnote,    //图片的脚标
                },
                {
                    type: para,    // 类型为段落
                    id: xxx,
                    text: xxx,
                    corresponding_medium: [{"type": "table", "id": "9-2", "offset": 77}]
                },
                {
                    type: title,     // 类型为标题
                    id: xxx, 
                    text: xxx,      //标题的文本
                    elements: [{
                                    type: table,  //类型为表格
                                    id: xxx, 
                                    table_title: xxx,     //表格的标题
                                    table_html: xxx,     //表格的 html 结构
                                    table_footnote: xxx,   //表格的脚标
                                    table_figure_url: xxx,   //表格图片的存储地址，没有存储就为 None
                                    table_trust: xxx,  //表格是否可信true of false
                                },
                                {
                                    type: para,
                                    id: xxx, 
                                    text: xxx,
                                    corresponding_medium: [{"type": "table", "id": "9-2", "offset": 77}]
                                }]
                }]
            },
    extra_info:{                //指南中提取的信息，其他格式不用管
                author: xxx, 
                chinese_keyword: xxx,
                english_keyword: xxx,
                ...
                }   
}
```

# 方案流程
![image](https://github.com/user-attachments/assets/47f7ee38-7718-4bdb-a4b3-a837431f65e0)
