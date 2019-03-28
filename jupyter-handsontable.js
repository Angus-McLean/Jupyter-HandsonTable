require.undef('jupyter-handsontable');

define('jupyter-handsontable', ['Handsontable'], function (Handsontable) {
    console.log('jupyter-handsontable2 has been required!', [Handsontable], Handsontable)

    var PERSISTENCE = {}

    function JupyterHandsonTable(name, elem, df, config) {
        // this = this || new JupyterHandsonTable()
        this.name = name;
        this.elem = elem;
        this.df = df;
        this.config = config;

        this.table_state = {};

        this.initTable()
        this.updateHot(df.data)
    }

    JupyterHandsonTable.ALL_TABLES = {}

    JupyterHandsonTable.prototype.initTable = function() {
        var _this = this;
        // Create necesary HTML
        var elem = this.elem;
        elem.style.width = '600px'
        elem.style.height = '400px'
        $(elem).append(`
            <div><button id="update_table">Update</button></div>
            <div id="chart-container"></div>
            <div id="pages"></div>
        `)

        // Init HandsonTable Object
        var hot = new Handsontable(elem.querySelectorAll('#chart-container')[0], {
            licenseKey: 'non-commercial-and-evaluation'
        });

        // Handle HandsonTable settings
        var df = this.df, config = this.config;
        var settings = Object.assign({
            colHeaders: df.columns,
            rowHeaders: df.index,
            contextMenu: true,
        }, config)
        settings = unpackSettings(settings);
        hot.updateSettings(settings)

        // Add event listeners
        Handsontable.dom.addEvent(elem.querySelectorAll('#update_table')[0], 'click', this.updateDf.bind(this));
        hot.addHook('beforeFilter', function (filters) {
            _this.table_state.filters = filters
            _this.fetchAndUpdate(_this.table_state)
            return false;
        })
        hot.addHook('beforeColumnSort', function (sorts) {
            _this.table_state.sorts = Array.from(arguments).filter(Array.isArray).flat()
            _this.fetchAndUpdate(_this.table_state)
            // return false; // needs to be commented so 
        })

        // Prevent Jupyter from capturing hotkeys when using the drop down
        if(!PERSISTENCE.htDropdownMenu) {
            var dropDownElem = document.querySelectorAll('.htDropdownMenu')
            if (!dropDownElem) return;
            dropDownElem[0].addEventListener('keydown', (e)=>{e.stopPropagation(); return false;})
            PERSISTENCE.htDropdownMenu = dropDownElem[0]
        }

        this.hot = hot;
        return hot
    }

    JupyterHandsonTable.prototype.updateDf = function () {
        var json_df = {
            columns : this.hot.getColHeader(),
            index : this.hot.getRowHeader(),
            data : this.hot.getData()
        }

        var updateHandsonTableCommand = `HandsonTable.update_table('${this.name}', '${JSON.stringify(json_df).replace(/\\/g,'\\\\')}')`
        sendToPy(updateHandsonTableCommand, console.log.bind(console, 'updateDf results'));
    }

    JupyterHandsonTable.prototype.fetchAndUpdate = function(fetchObj) {
        console.log('fetchAndUpdate', this, arguments);
        var _this = this;
        
        var updateHandsonTableCommand = `HandsonTable.query_table('${this.name}', '${JSON.stringify(fetchObj).replace(/\\/g,'\\\\')}')`

        console.log(updateHandsonTableCommand);
        sendToPy(updateHandsonTableCommand, function(resp) {
            console.log('HandsonTable.query_table callback', resp);
            // NOTE : if parsing doesn't work make sure python isn't printing anything.. (that'll break your python command output)
            var serverDf = JSON.parse(JSON.parse(resp.content.text))
            _this.updateHot(serverDf.data);
        });
        
        // return false;
    }

    JupyterHandsonTable.prototype.updateHot = function (data) {
        this.hot.loadData(data);
    }


    /* 
     * Static Methods
    */
    function unpackSettings(settings) {
        if(settings.maxColWidth) {
            settings.modifyColWidth = function(width, col) {
                if (width > settings.maxColWidth) {
                    return settings.maxColWidth
                }
            }
        }
        
        return settings
    }

    function sendToPy(command, callback) {
        var callbacks = {
        silent:false,
        iopub : {output : callback}
        }
        IPython.notebook.kernel.execute('print('+command+')', callbacks)
    }

    window.JupyterHandsonTable = JupyterHandsonTable;
    return JupyterHandsonTable;
})