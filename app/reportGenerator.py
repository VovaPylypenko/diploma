class ReportGenerator:

    @staticmethod
    def add_td(text, style=""):
        return f'<td {style}> XMLToString({text}) </td>'

    @staticmethod
    def create_table(error_blocks, status, style):
        error_table = ''

        for error_block in error_blocks:
            error_table += f'<tr>'
            # all failures in single block have the same errorID and failed version list
            error_table += ReportGenerator.add_td(error_block[0].msg, style)
            print('--\n' + error_block[0].msg)
            print('++\n')
            print(error_block[0].msg)

            tests_str = ''
            if not error_block[1].tests or len(error_block[1].tests) != 0:
                tests_str = '<details><summary>ALL TESTS</summary>'
                for test in sorted(error_block[1].tests):
                    tests_str += f'{test}<br>'
                tests_str += '</details>'

            error_table += ReportGenerator.add_td(tests_str)
            error_table += ReportGenerator.add_td(status, style)
            error_table += ReportGenerator.add_td(error_block[1].count, 'class="data" align="left"')

            error_table += ReportGenerator.add_td(error_block[1].first_version)
            failed_versions_str = ''
            for failedVersion in error_block[1].last_versions:
                failed_versions_str += f'{failedVersion}<br>'
            error_table += ReportGenerator.add_td(failed_versions_str)
            error_table += f'</tr>'

        return error_table

    @staticmethod
    def create_new_table(new_error_list):
        return ReportGenerator.create_table(new_error_list, 'New', 'class="failed data"')

    @staticmethod
    def create_replay_table(replay_error_list):
        return ReportGenerator.create_table(replay_error_list, 'Replay', 'class="replay data"')

    @staticmethod
    def create_old_table(old_error_list):
        return ReportGenerator.create_table(old_error_list, 'Old', 'class="data"')

    @staticmethod
    def add_style():
        return f'''<style>
                table
                {'{'}
                    border-collapse: collapse;
                    border: 1px solid black;
                    width:1900px;
                {'}'}

                tr
                {'{'}
                    border:0;
                    color:#DD0000;
                {'}'}

                th
                {'{'}
                    height:20px;
                    color:#727092;
                    font-size:12px;
                    font-weight:bold;
                    font-family:Verdana;
                    border: 1px solid #F0F0F0;
                {'}'}

                td
                {'{'}
                    margin:0;
                    height:20px;
                    color:#9A95B0;
                    font-size:10px;
                    font-weight:bold;
                    font-family:Verdana;
                    border: 1px solid #F0F0F0;
                {'}'}

                noborder
                {'{'}
                    width: 100%;
                    border: 0px;
                {'}'}

                p.header
                {'{'}
                    color:#727092;
                    font-size:14px;
                    font-weight:bold;
                    font-family:Verdana;
                {'}'}

                td.name
                {'{'}
                    padding-left:0px;
                    text-align:left;
                {'}'}

                td.data
                {'{'}
                    padding-left:0px;
                    text-align:center;
                {'}'}

                td.failed
                {'{'}
                    color:#FF0000;
                {'}'}

                td.skipped
                {'{'}
                    color:#E18B6B;
                {'}'}
                td.passed
                {'{'}
                    color:#347235;
                {'}'}

                td.replay
                {'{'}
                    color:#505250;
                {'}'}

                td.inInspection
                {'{'}
                    color:#4A0AD0;
                {'}'}

                .description
                {'{'}
                    overflow:hidden;
                    white-space:nowrap;
                    width: 50%;
                {'}'}

                th.failed
                {'{'}
                    height:12px;
                    color:#FF0000;
                    background:#FF0000;
                {'}'}
                th.skipped
                {'{'}
                    height:12px;
                    color:#E18B6B;
                    background:#E18B6B;
                {'}'}
                th.passed
                {'{'}
                    height:12px;
                    color:#347235;
                    background:#347235;
                {'}'}
            </style>'''

    @staticmethod
    def write_fails_2_HTML(gERRORS, data_save_path, version):
        # Group tests by failure + failed version list, otherwise create new entry
        # if defect failedVersion has id = len(totalFailedVersions) and len(defectFailedVersion) == 1, this is new defect
        # if defect failedVersion has id = len(totalFailedVersions) and len(defectFailedVersion) > 1, this is replay defect
        # otherwise this is old defect

        new_errors = []
        replay_errors = []
        old_errors = []

        for error, failure in gERRORS.items():
            if failure.first_version == version and failure.count == 1:
                print('-1-')
                print(error.msg)
                print('-2-')
                print(error.msg_transformed)
                new_errors.append([error, failure])
            else:
                if version in failure.last_versions:
                    replay_errors.append([error, failure])
                else:
                    old_errors.append([error, failure])

        ReportGenerator._writeFailsToHTML(new_errors, replay_errors, old_errors, data_save_path)

    @staticmethod
    def _writeFailsToHTML(new_errors, replay_errors, old_errors, data_save_path):
        f = open(data_save_path + '/reportSFManager.html', 'w')

        message = f'''<html>
        <head>
            {ReportGenerator.add_style()}
        </head>
        <body> 
            <table class = "defect">
                <tr align ="center" width="99%">
                    <th width="40%"> Name </th>
                    <th width="44%"> Test </th>
                    <th width="3%"> Status </th>
                    <th width="3%"> Count </th>
                    <th width="5%"> First failed version </th>
                    <th width="5%"> Last 5 failed versions </th>
                </tr>
                {ReportGenerator.create_new_table(new_errors)}
                {ReportGenerator.create_replay_table(replay_errors)}
                {ReportGenerator.create_old_table(old_errors)}
            </table>
        </body>
        <script type="text/javascript" language="javascript">
            function XMLToString(oXML){{
                if (window.ActiveXObject){{
                    var oString = oXML.xml;
                    return oString;
                }}else{{
                    return (new XMLSerializer()).serializeToString(oXML);
                }}
            }}
        </script>
        </html>'''

        f.write(message)
        f.close()

