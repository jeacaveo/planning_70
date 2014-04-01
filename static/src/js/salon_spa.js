openerp.salon_spa = function(instance){
    var module = instance.web_calendar

    module.CalendarView.include({
        init: function(parent, dataset, view_id, options)
        {
            this._super(parent, dataset, view_id, options);
            this.unit_resource_field = '';
            this.resource_fields={};
            this.first_load = true;  // TODO undo force
            // key = salon.spa.appointment category_id
            this.color_map = {'1': '#C0C0C0'}; 
            return this
        },
        events_loaded: function(events, fn_filter, no_filter_reload) {
            // this._super();  // calling the original Foo.bar() method
            if($.isEmptyObject(this.resource_fields))
            {
                return this._super(events, fn_filter, no_filter_reload);
            }

            var self = this;

            var filter_values = jQuery.extend({}, this.resource_fields);
            for(var field in filter_values)
            {
                filter_values[field] = {};
            }
            if(this.color_field)
            {
                filter_values[this.color_field] = {};
            }

            var calendar_events=[]
            for(var e = 0; e < events.length; e++)
            {
                events[e].textColor = '#000';
                for(var field in filter_values)
                {
                    field_value = (typeof events[e][field] === 'object') ? events[e][field][0] : events[e][field];
                    field_label = (typeof events[e][field] === 'object') ? events[e][field][1] : events[e][field];
                    if(field_value && !filter_values[field][field_value])
                    {
                        filter_values[field][field_value]={
                            value: field_value,
                            label: field_label,
                            color: 'inherit',
                            textColor: 'inherit',
                        };
                    }
                    if(field == self.color_field)
                    {
                        events[e].color = filter_values[field][field_value].color = self.get_color(field_value);
                        events[e].textColor = filter_values[field][field_value].textColor = '#fff';
                    }
                }
                if(typeof(fn_filter) === 'function' && !fn_filter(events[e]))
                {
                    continue;
                }

                if (this.fields[this.date_start]['type'] == 'date')
                {
                    events[e][this.date_start] = openerp.web.auto_str_to_date(events[e][this.date_start]).set({hour: 9}).toString('yyyy-MM-dd HH:mm:ss');
                }
                if (this.date_stop && events[e][this.date_stop] && this.fields[this.date_stop]['type'] == 'date') {
                    events[e][this.date_stop] = openerp.web.auto_str_to_date(events[e][this.date_stop]).set({hour: 17}).toString('yyyy-MM-dd HH:mm:ss');
                }
                calendar_events.push(this.convert_event(events[e]));
            }
            if (!no_filter_reload && this.sidebar && !$.isEmptyObject(this.resource_fields))
            {
                _(this.sidebar.resource_filters).each(function(filter, filter_field)
                {
                    if(self.unit_resource_field == filter_field)
                    {
                        var list = _.map(
                            filter_values[filter_field],
                            function(filter, id)
                            {
                                return {key: id, label: filter.label};
                            });

                        if(list.length == 0)
                        {
                            list = [{key: '', label: scheduler.templates.day_date(scheduler.getState().date)}];
                        }

                        scheduler.createUnitsView({
                            name:"unit",
                            property: self.unit_resource_field,
                            list: list,
                        });
                        scheduler.createTimelineView({
                            name:"timeline",
                            x_unit:"hour",
                            x_date:"%H", 
                            x_step: 2,
                            x_size: 10,
                            x_start: 4,
                            x_length: 8,
                            y_unit: list,
                            y_property: self.unit_resource_field,
                            render: "bar",
                            second_scale: {
                                x_unit: "day",
                                x_date: "%F %d"
                            }
                        });
                    }
                    filter.events_loaded(filter_values[filter_field]);
                });

                // TODO refactor this so day/unit tab is selected on menu first load.
                if (this.first_load){
                    $('#salon_spa_unit_tab').click();
                    this.first_load = false;
                }
            }

            this.resource_filter_values = filter_values;
            scheduler.parse(calendar_events, 'json');

            this.refresh_scheduler();
        },
    });
};
